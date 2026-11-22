# -*- coding: utf-8 -*-
"""
Created on Mon Nov 16 14:34:18 2026

@author: mohak
"""


from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Any
import threading
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from api.integrations.supabase_client import get_supabase_client
from api.research.models import ResearchRequest
from api.research_agent.agent import (
    propose_next_experiment,
    get_agent_provider,
)
from api.research_agent.guardrails import (
    Agent2GuardrailError,
    validate_agent_2_proposal,
)
from api.research_agent.models import Agent2Request
from api.research_assistant.conversation import router as conversation_router
from api.data.github_data import ResearchDataRepository
from api.research.executor import execute_research
from api.research.experiment_api import (
    SaveExperimentRequest,
    save_experiment,
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ai-research",
    tags=["ai-research-assistant"],
)
router.include_router(conversation_router)

# ============================================================
# REQUEST MODELS
# ============================================================

class CreateSessionRequest(BaseModel):
    title: str = Field(
        default="New Research Chat",
        min_length=1,
        max_length=120,
    )


class ProposalRequest(BaseModel):
    research_question: str = Field(min_length=5, max_length=1000)
    hypothesis: str = Field(min_length=5, max_length=1000)
    base_research_request: ResearchRequest


class ApprovalRequest(BaseModel):
    acknowledge_development_only: bool = False


class RejectionRequest(BaseModel):
    reason: str = Field(default="Rejected by user", max_length=1000)
    
# ============================================================
# HELPERS
# ============================================================

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _db():
    return get_supabase_client()


def _first_row(response: Any) -> dict:
    rows = response.data or []
    if not rows:
        raise RuntimeError("Database operation returned no record.")
    return rows[0]


def _tokens_used(usage: dict) -> int:
    total = usage.get("total_tokens")

    if total is not None:
        return int(total)

    input_tokens = (
        usage.get("input_tokens")
        or usage.get("prompt_tokens")
        or 0
    )
    output_tokens = (
        usage.get("output_tokens")
        or usage.get("completion_tokens")
        or 0
    )

    return int(input_tokens) + int(output_tokens)


def _get_session(session_id: UUID) -> dict:
    response = (
        _db()
        .table("chat_sessions")
        .select("id,title,status")
        .eq("id", str(session_id))
        .limit(1)
        .execute()
    )

    rows = response.data or []

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Research chat session not found.",
        )

    if rows[0]["status"] != "active":
        raise HTTPException(
            status_code=409,
            detail="This research chat session is not active.",
        )

    return rows[0]


# ============================================================
# SESSION MANAGEMENT
# ============================================================

@router.post("/sessions", status_code=201)
def create_session(request: CreateSessionRequest) -> dict:
    try:
        row = _first_row(
            _db()
            .table("chat_sessions")
            .insert({
                "title": request.title.strip(),
                "status": "active",
                "metadata": {},
            })
            .execute()
        )

        return {
            "success": True,
            "session": row,
        }

    except Exception as exc:
        logger.exception("Could not create research session")
        raise HTTPException(
            status_code=502,
            detail="Could not create research session.",
        ) from exc


@router.get("/sessions")
def list_sessions() -> dict:
    try:
        response = (
            _db()
            .table("chat_sessions")
            .select("*")
            .order("updated_at", desc=True)
            .limit(50)
            .execute()
        )

        return {
            "sessions": response.data or [],
        }

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not load research sessions.",
        ) from exc


@router.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: UUID) -> dict:
    _get_session(session_id)

    try:
        response = (
            _db()
            .table("chat_messages")
            .select("*")
            .eq("session_id", str(session_id))
            .order("created_at", desc=False)
            .limit(200)
            .execute()
        )

        return {
            "session_id": str(session_id),
            "messages": response.data or [],
        }

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not load chat messages.",
        ) from exc


# ============================================================
# PROPOSAL WORKFLOW — FIRST VERTICAL SLICE
# ============================================================

@router.post("/sessions/{session_id}/propose")
def propose_experiment(
    session_id: UUID,
    request: ProposalRequest,
) -> dict:

    session = _get_session(session_id)
    db = _db()

    run_id = str(uuid4())
    thread_id = str(session_id)
    provider = get_agent_provider()
    started_at = _now()

    agent_request = Agent2Request(
        research_question=request.research_question,
        hypothesis=request.hypothesis,
        base_research_request=request.base_research_request,
        latest_result={},
        experiment_history=[],
    )

    try:
        # 1. Persist the user's question.
        db.table("chat_messages").insert({
            "session_id": str(session_id),
            "role": "user",
            "content": request.research_question,
            "metadata": {
                "hypothesis": request.hypothesis,
            },
        }).execute()

        # 2. Create a durable agent-run record.
        db.table("agent_runs").insert({
            "id": run_id,
            "session_id": str(session_id),
            "thread_id": thread_id,
            "status": "running",
            "current_step": "generating_proposal",
            "provider": provider,
            "input_data": agent_request.model_dump(mode="json"),
            "output_data": {},
            "started_at": started_at,
        }).execute()

        # 3. Reuse existing Agent 2. Do not modify its logic.
        response = propose_next_experiment(agent_request)

        # 4. Apply existing deterministic guardrails.
        validated = validate_agent_2_proposal(
            agent_request,
            response.proposal,
        )

        proposal_data = validated.model_dump(mode="json")
        usage = response.usage or {}
        token_count = _tokens_used(usage)

        # 5. Persist generated output before creating the ledger entry.
        db.table("agent_runs").update({
            "status": "running",
            "current_step": "saving_proposal",
            "model": response.model,
            "tokens_used": token_count,
            "output_data": {
                "proposal": proposal_data,
                "usage": usage,
            },
        }).eq("id", run_id).execute()

        # 6. Create the research ledger entry.
        ledger = _first_row(
            db.table("research_ledger").insert({
                "session_id": str(session_id),
                "agent_run_id": run_id,
                "hypothesis": validated.hypothesis,
                "hypothesis_family": None,
                "status": "proposed",
                "approval_status": "pending",
                "proposal": proposal_data,
                "decision": {},
                "evidence_summary": {},
            }).execute()
        )

        # 7. Persist the assistant's response.
        db.table("chat_messages").insert({
            "session_id": str(session_id),
            "role": "assistant",
            "content": (
                f"Experiment proposal: {validated.research_question}\n\n"
                f"Hypothesis: {validated.hypothesis}\n\n"
                f"Rationale: {validated.rationale}\n\n"
                f"Expected learning: {validated.expected_learning}\n\n"
                "This proposal has not been executed. "
                "Explicit approval is required."
            ),
            "metadata": {
                "agent_run_id": run_id,
                "ledger_id": ledger["id"],
                "proposal": proposal_data,
            },
        }).execute()

        # 8. Mark the run as awaiting human approval.
        db.table("agent_runs").update({
            "status": "awaiting_approval",
            "current_step": "awaiting_human_approval",
            "completed_at": _now(),
            "updated_at": _now(),
        }).eq("id", run_id).execute()

        # 9. Update session activity.
        db.table("chat_sessions").update({
            "updated_at": _now(),
        }).eq("id", str(session_id)).execute()

        return {
            "success": True,
            "session_id": str(session_id),
            "agent_run_id": run_id,
            "ledger_id": ledger["id"],
            "status": "awaiting_approval",
            "proposal": proposal_data,
            "model": response.model,
            "usage": usage,
        }

    except Agent2GuardrailError as exc:
        _mark_failed(db, run_id, str(exc))
        raise HTTPException(
            status_code=422,
            detail=f"Proposal rejected by research guardrails: {exc}",
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Research proposal workflow failed. Run ID: %s",
            run_id,
        )
        _mark_failed(db, run_id, str(exc))
        raise HTTPException(
            status_code=502,
            detail=f"Could not complete research proposal: {type(exc).__name__}: {exc}",
        ) from exc


def _mark_failed(db, run_id: str, error: str) -> None:
    """Best-effort failure persistence; never hides the original error."""
    try:
        db.table("agent_runs").update({
            "status": "failed",
            "current_step": "failed",
            "error_message": error[:2000],
            "completed_at": _now(),
            "updated_at": _now(),
        }).eq("id", run_id).execute()
    except Exception:
        pass


# ============================================================
# APPROVAL, EXECUTION AND RESULT INTERPRETATION
# ============================================================

def _get_ledger_entry(db, session_id: str, ledger_id: str) -> dict:
    response = (
        db.table("research_ledger")
        .select("*")
        .eq("id", ledger_id)
        .eq("session_id", session_id)
        .limit(1)
        .execute()
    )

    rows = response.data or []
    if not rows:
        raise HTTPException(status_code=404, detail="Research proposal not found.")

    return rows[0]


def _compact_evidence(result: dict) -> dict:
    """Only send aggregate metrics and diagnostics to the LLM."""
    evidence = {}

    for stage in ("development", "validation", "final_holdout"):
        stage_result = result.get(stage)

        if not isinstance(stage_result, dict):
            evidence[stage] = None
            continue

        evidence[stage] = {
            "summary": stage_result.get("summary", {}),
            "performance": stage_result.get("performance", {}),
            "diagnostics": stage_result.get("diagnostics", {}),
            "random_baseline": stage_result.get("random_baseline", {}),
            "warnings": stage_result.get("warnings", []),
        }

    return {
        "research_config": {
            key: result.get("research_config", {}).get(key)
            for key in (
                "research_question",
                "hypothesis",
                "development_start",
                "development_end",
                "validation_start",
                "validation_end",
                "holdout_start",
                "holdout_end",
                "evaluation_horizons",
                "temporal_convention",
            )
        },
        "stages": evidence,
    }


def _interpret_evidence(evidence: dict) -> tuple[str, dict]:
    """
    Gemini explains deterministic engine output.
    It does not calculate or modify research metrics.
    """
    import json
    import os
    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    model = os.getenv(
        "RESEARCH_INTERPRETATION_MODEL",
        "gemini-3.5-flash-lite",
    )

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are interpreting results from a deterministic stock research engine.

Rules:
- Do not calculate or invent any metric.
- Use only the supplied evidence.
- Distinguish development, validation and final holdout.
- Explicitly state when validation or holdout is absent.
- Discuss transaction costs and random baseline only if evidence is supplied.
- Do not call a strategy profitable or robust merely because a metric is positive.
- Identify sample-size limitations and warnings when present.
- If evidence is insufficient, say so.
- Keep the interpretation concise and structured.

Return:
1. What the experiment tested
2. What the evidence shows
3. What it does not establish
4. Recommended next research step

Evidence:
{json.dumps(evidence, default=str)[:18000]}
"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=700,
        ),
    )

    usage_metadata = getattr(response, "usage_metadata", None)

    usage = {
        "input_tokens": getattr(usage_metadata, "prompt_token_count", 0) or 0,
        "output_tokens": getattr(usage_metadata, "candidates_token_count", 0) or 0,
        "total_tokens": getattr(usage_metadata, "total_token_count", 0) or 0,
        "provider": "gemini",
    }

    interpretation = getattr(response, "text", None)
    if not interpretation:
        raise RuntimeError("Gemini returned an empty interpretation.")

    return interpretation, usage


def _execute_approved_research(
    session_id: str,
    ledger_id: str,
    run_id: str,
) -> None:
    """
    Execute an approved proposal.

    The Python research engine is the source of truth.
    GitHub stores the canonical experiment.
    Supabase stores workflow state and compact evidence.
    """
    db = _db()

    claim = (
        db.table("agent_runs")
        .update({
            "status": "running",
            "current_step": "executing_research",
            "updated_at": _now(),
        })
        .eq("id", run_id)
        .eq("status", "pending")
        .select("id")
        .execute()
    )

    # Another worker already claimed this run, or it is not queued.
    if not claim.data:
        return

    try:
        ledger = _get_ledger_entry(db, session_id, ledger_id)

        if ledger.get("approval_status") != "approved":
            raise RuntimeError("Research proposal is not approved.")

        proposal = ledger["proposal"]
        research_request = ResearchRequest.model_validate(
            proposal["research_request"]
        )

        # The conditional pending -> running update above is the sole
        # execution claim; do not overwrite it with an unconditional update.

        # Run the existing deterministic research engine.
        result = execute_research(
            research_request,
            repository=ResearchDataRepository(),
        )

        # Attach proposal context to the canonical result.
        result["research_config"]["research_question"] = (
            proposal["research_question"]
        )
        result["research_config"]["hypothesis"] = (
            proposal["hypothesis"]
        )
        result["research_config"]["experiment_type"] = (
            proposal["experiment_type"]
        )

        db.table("agent_runs").update({
            "current_step": "saving_experiment_to_github",
            "updated_at": _now(),
        }).eq("id", run_id).execute()

        # Save through the existing canonical experiment storage.
        saved = save_experiment(
            SaveExperimentRequest(
                research_result=result,
                name=proposal["research_question"][:120],
                notes="Created by AI Research Assistant after explicit approval.",
                parent_experiment_id=proposal.get("parent_experiment_id"),
                source_agent_run_id=run_id,
            )
        )

        evidence = _compact_evidence(result)

        db.table("agent_runs").update({
            "current_step": "interpreting_results",
            "updated_at": _now(),
        }).eq("id", run_id).execute()

        interpretation = None
        interpretation_usage = {}

        try:
            interpretation, interpretation_usage = _interpret_evidence(
                evidence
            )
        except Exception:
            logger.exception("AI interpretation failed for run %s", run_id)
            interpretation = (
                "The experiment completed and its results were saved. "
                "AI interpretation was unavailable; inspect the recorded "
                "metrics directly."
            )

        evidence["experiment_id"] = saved["experiment_id"]
        evidence["commit_sha"] = saved["commit_sha"]
        evidence["interpretation"] = interpretation

        db.table("research_ledger").update({
            "status": "completed",
            "evidence_summary": evidence,
            "decision": {
                "execution_status": "completed",
                "experiment_id": saved["experiment_id"],
                "commit_sha": saved["commit_sha"],
            },
            "github_experiment_id": saved["experiment_id"],
            "github_commit_sha": saved["commit_sha"],
            "updated_at": _now(),
        }).eq("id", ledger_id).execute()

        db.table("agent_runs").update({
            "status": "completed",
            "current_step": "completed",
            "output_data": {
                "experiment_id": saved["experiment_id"],
                "commit_sha": saved["commit_sha"],
                "evidence": evidence,
                "interpretation_usage": interpretation_usage,
            },
            "completed_at": _now(),
            "updated_at": _now(),
        }).eq("id", run_id).execute()

        db.table("chat_messages").insert({
            "session_id": session_id,
            "role": "assistant",
            "content": (
                f"Research experiment completed: {saved['experiment_id']}\n\n"
                f"{interpretation}"
            ),
            "metadata": {
                "agent_run_id": run_id,
                "ledger_id": ledger_id,
                "experiment_id": saved["experiment_id"],
                "commit_sha": saved["commit_sha"],
            },
        }).execute()

        db.table("chat_sessions").update({
            "updated_at": _now(),
        }).eq("id", session_id).execute()

    except Exception as exc:
        logger.exception("Approved research execution failed: %s", run_id)

        try:
            db.table("agent_runs").update({
                "status": "failed",
                "current_step": "failed",
                "error_message": str(exc)[:2000],
                "completed_at": _now(),
                "updated_at": _now(),
            }).eq("id", run_id).execute()

            db.table("research_ledger").update({
                "status": "failed",
                "decision": {
                    "execution_status": "failed",
                    "error": str(exc)[:1000],
                },
                "updated_at": _now(),
            }).eq("id", ledger_id).execute()

        except Exception:
            logger.exception("Could not persist execution failure.")


@router.post("/sessions/{session_id}/ledger/{ledger_id}/approve")
def approve_proposal(
    session_id: UUID,
    ledger_id: UUID,
    background_tasks: BackgroundTasks,
    request: ApprovalRequest,
) -> dict:

    _get_session(session_id)
    db = _db()

    ledger = _get_ledger_entry(
        db,
        str(session_id),
        str(ledger_id),
    )

    if ledger.get("approval_status") != "pending":
        raise HTTPException(
            status_code=409,
            detail="This proposal has already been approved or rejected.",
        )

    proposal_request = ResearchRequest.model_validate(
        ledger["proposal"]["research_request"]
    )

    development_only = (
        proposal_request.validation_start is None
        or proposal_request.holdout_start is None
    )

    if development_only and not request.acknowledge_development_only:
        raise HTTPException(
            status_code=400,
            detail=(
                "This proposal has no complete validation and holdout stages. "
                "Explicitly acknowledge development-only execution to proceed."
            ),
        )

    # Conditional update: only one approval request can claim this proposal.
    claimed = (
        db.table("research_ledger")
        .update({
            "approval_status": "approved",
            "updated_at": _now(),
        })
        .eq("id", str(ledger_id))
        .eq("session_id", str(session_id))
        .eq("approval_status", "pending")
        .select("*")
        .execute()
    )

    if not claimed.data:
        raise HTTPException(
            status_code=409,
            detail="Proposal approval was already processed.",
        )

    run_id = ledger["agent_run_id"]

    queued = (
        db.table("agent_runs").update({
            "status": "pending",
            "current_step": "queued_for_execution",
            "updated_at": _now(),
        }).eq("id", run_id).eq("status", "awaiting_approval")
        .select("id").execute()
    )
    if not queued.data:
        db.table("research_ledger").update({
            "approval_status": "pending", "updated_at": _now(),
        }).eq("id", str(ledger_id)).eq("approval_status", "approved").execute()
        raise HTTPException(status_code=409, detail="Could not queue this approved research run.")

    background_tasks.add_task(
        _execute_approved_research,
        str(session_id),
        str(ledger_id),
        run_id,
    )

    return {
        "success": True,
        "status": "approved",
        "execution_status": "queued",
        "agent_run_id": run_id,
        "ledger_id": str(ledger_id),
        "development_only": development_only,
    }


@router.post("/sessions/{session_id}/ledger/{ledger_id}/reject")
def reject_proposal(
    session_id: UUID,
    ledger_id: UUID,
    request: RejectionRequest,
) -> dict:

    _get_session(session_id)
    db = _db()

    _get_ledger_entry(db, str(session_id), str(ledger_id))

    result = (
        db.table("research_ledger")
        .update({
            "approval_status": "rejected",
            "status": "rejected",
            "decision": {
                "reason": request.reason,
                "decided_at": _now(),
            },
            "updated_at": _now(),
        })
        .eq("id", str(ledger_id))
        .eq("session_id", str(session_id))
        .eq("approval_status", "pending")
        .select("*")
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=409,
            detail="Proposal approval was already processed.",
        )

    db.table("agent_runs").update({
        "status": "cancelled",
        "current_step": "rejected_by_user",
        "completed_at": _now(),
        "updated_at": _now(),
    }).eq("id", result.data[0]["agent_run_id"]).execute()

    return {
        "success": True,
        "status": "rejected",
        "ledger_id": str(ledger_id),
    }


@router.get("/sessions/{session_id}/runs/{run_id}")
def get_agent_run(session_id: UUID, run_id: UUID) -> dict:

    _get_session(session_id)

    response = (
        _db()
        .table("agent_runs")
        .select("*")
        .eq("id", str(run_id))
        .eq("session_id", str(session_id))
        .limit(1)
        .execute()
    )

    rows = response.data or []

    if not rows:
        raise HTTPException(status_code=404, detail="Agent run not found.")

    return {
        "success": True,
        "run": rows[0],
    }


def resume_interrupted_runs() -> int:
    """Recover approved runs after restart; currently single-worker only."""
    db = _db()
    response = (
        db.table("research_ledger")
        .select("id,session_id,agent_run_id,approval_status")
        .eq("approval_status", "approved").execute()
    )
    recovered = 0
    for ledger in response.data or []:
        run_id = ledger.get("agent_run_id")
        if not run_id:
            continue
        run_response = db.table("agent_runs").select("id,status").eq("id", run_id).limit(1).execute()
        runs = run_response.data or []
        if not runs:
            logger.error("Approved ledger %s has no run %s.", ledger.get("id"), run_id)
            continue
        status = runs[0].get("status")
        if status == "running":
            reset = (
                db.table("agent_runs").update({
                    "status": "pending",
                    "current_step": "recovered_after_restart",
                    "updated_at": _now(),
                }).eq("id", run_id).eq("status", "running")
                .select("id").execute()
            )
            if not reset.data:
                continue
        elif status != "pending":
            continue
        threading.Thread(
            target=_execute_approved_research,
            args=(ledger["session_id"], ledger["id"], run_id),
            daemon=True, name=f"research-recovery-{run_id}",
        ).start()
        recovered += 1
    logger.info("Recovered %s approved research runs.", recovered)
    return recovered
