
from __future__ import annotations
# -*- coding: utf-8 -*-
"""
Created on Sun Nov 22 16:40:34 2026

@author: mohak
"""

import json
import logging
import os
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.integrations.supabase_client import get_supabase_client
from api.research_agent.models import Agent2Proposal
from api.research_workflow.graph import (
    run_follow_up_research_design,
    run_initial_research_design,
)
from api.research_workflow.intent_router import (
    build_experiment_context,
    resolve_research_action,
)

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_INTENTS = {
    "research_question",
    "propose_experiment",
    "explain_experiment",
    "compare_experiments",
    "out_of_scope",
    "needs_clarification",
}

ALLOWED_RESEARCH_ACTIONS = {
    "new_research",
    "follow_up",
    "ambiguous",
}


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    client_message_id: str = Field(min_length=8, max_length=100)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_active_session(session_id: UUID) -> dict:
    response = (
        get_supabase_client()
        .table("chat_sessions")
        .select("id,title,status")
        .eq("id", str(session_id))
        .limit(1)
        .execute()
    )

    rows = response.data or []

    if not rows:
        raise HTTPException(404, "Research chat session not found.")

    if rows[0].get("status") != "active":
        raise HTTPException(409, "This research chat session is not active.")

    return rows[0]


def _load_recent_messages(
    session_id: UUID,
    limit: int = 10,
) -> list[dict]:
    response = (
        get_supabase_client()
        .table("chat_messages")
        .select("role,content")
        .eq("session_id", str(session_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return list(reversed(response.data or []))


def _load_session_experiments(
    session_id: UUID,
    limit: int = 15,
) -> list[dict]:
    """
    Load only this session's experiment ledger records.

    The LLM receives a compact reference list. The full validated
    request and evidence remain server-side.
    """

    response = (
        get_supabase_client()
        .table("research_ledger")
        .select(
            "id,hypothesis,proposal,evidence_summary,status,"
            "approval_status,created_at"
        )
        .eq("session_id", str(session_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    return build_experiment_context(response.data or [])


def _response_budget(message: str) -> int:
    text = message.lower()

    technical_terms = (
        "hypothesis", "backtest", "statistics", "regression",
        "confidence interval", "p-value", "look-ahead",
        "lookahead", "temporal", "validation", "holdout",
        "feature", "model", "algorithm", "formula",
        "architecture", "implementation", "risk",
    )

    detailed_phrases = (
        "explain in detail", "step by step", "deep dive",
        "compare", "evaluate", "analyse", "analyze",
        "how should i", "why does", "what happens if",
    )

    if (
        any(term in text for term in technical_terms)
        or any(phrase in text for phrase in detailed_phrases)
        or len(text) > 350
    ):
        return 1400

    if len(text) < 90:
        return 500

    return 900


def _call_research_router(
    messages: list[dict],
    latest_user_message: str,
    available_experiments: list[dict] | None = None,
) -> tuple[dict, dict]:

    from google import genai
    from google.genai import types

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    model = os.getenv(
        "RESEARCH_ROUTER_MODEL",
        os.getenv(
            "RESEARCH_AGENT_MODEL",
            "gemini-3.5-flash-lite",
        ),
    )

    client = genai.Client(api_key=api_key)

    # Expose only identifiers and short descriptions to the classifier.
    experiment_references = [
        {
            "experiment_id": item["experiment_id"],
            "hypothesis": item.get("hypothesis", ""),
            "status": item.get("status", ""),
        }
        for item in (available_experiments or [])
    ]

    system_prompt = """
You are the conversational research assistant for Stock Scanner.

Your role is to help the user understand markets, statistics,
research methodology, hypotheses and the Stock Scanner platform.

You are a knowledgeable technical assistant, not a generic chatbot.

CAPABILITIES:
- Explain finance, stock-market and technical-analysis concepts.
- Explain statistics, probability, hypothesis testing and ML concepts.
- Discuss backtesting, temporal validation, leakage and research design.
- Help formulate and critique research hypotheses.
- Discuss existing experiments only when their evidence is available.
- Identify whether the user wants a new experiment or a follow-up.

LIMITATIONS:
- Live web search and current market data are not connected.
- Do not claim to have executed an experiment from this chat.
- Do not invent experiment results, stock prices, financial figures,
  historical data or unsupported feature-engine capabilities.
- The deterministic Python research engine owns all calculations.

ANSWER QUALITY:
1. Answer the actual question first.
2. Explain intuition before technical terminology where useful.
3. Explain assumptions and limitations for statistical questions.
4. For hypotheses, discuss rationale, measurable outcome,
   comparison/baseline, confounders and failure modes.
5. Ask one focused clarification only when essential information
   is missing. Do not turn every question into an experiment.
6. Never invent capabilities that the application does not have.
7. Be honest when evidence is insufficient.
8. Avoid unnecessary repetition and filler.

INTENT CLASSIFICATION:
- research_question: conceptual or technical research discussion.
- propose_experiment: the user wants an experiment proposal.
- explain_experiment: the user asks about an existing experiment.
- compare_experiments: the user wants experiments compared.
- out_of_scope: unrelated request.
- needs_clarification: essential information is missing.

RESEARCH ACTION CLASSIFICATION:

When intent is "propose_experiment", also classify research_action:

1. "new_research":
   The user clearly wants a new, independent experiment or a different
   hypothesis. Previous experiments are not the baseline.

2. "follow_up":
   The user clearly wants to improve, modify, extend or retest a
   specific previous experiment. Examples:
   - "Add a volume filter to EXP-123."
   - "Can we improve the previous RSI experiment?"
   - "Test the same setup but with a different threshold."

   If the user clearly refers to a previous experiment, set
   referenced_experiment_id to its exact ID from AVAILABLE EXPERIMENTS.

3. "ambiguous":
   Use this when you cannot confidently distinguish a new experiment
   from an improvement, or cannot identify which previous experiment
   the user means.

IMPORTANT:
- Do not assume that every new hypothesis is a follow-up.
- Do not assume that every message mentioning a previous experiment
  means the user wants to modify it.
- "Let's test something else" is normally new_research if it clearly
  means a separate investigation; otherwise use ambiguous.
- "Improve it" without a clear antecedent is ambiguous.
- Never invent an experiment ID.
- Only select IDs present in AVAILABLE EXPERIMENTS.
- If the user says "new experiment" or "independent experiment",
  choose new_research even if prior experiments exist.
- If the user says "improve", "modify", "extend" or "add a condition"
  but the target is unclear, choose ambiguous.
- For non-proposal intents, set research_action to null and
  referenced_experiment_id to null.

Return one valid JSON object with exactly these keys:
{
  "intent": "...",
  "response": "Markdown answer shown to the user",
  "needs_follow_up": false,
  "follow_up_question": "",
  "research_question": "",
  "hypothesis": "",
  "research_action": null,
  "referenced_experiment_id": null
}

A proposed experiment is only a research idea. Do not claim it has
been configured, approved or executed.

Return valid JSON only. Do not use Markdown fences around the JSON.
"""

    prompt = (
        system_prompt
        + "\n\nAVAILABLE EXPERIMENTS:\n"
        + json.dumps(
            experiment_references,
            ensure_ascii=False,
            default=str,
        )
        + "\n\nRECENT CONVERSATION:\n"
        + json.dumps(
            messages,
            ensure_ascii=False,
            default=str,
        )
        + "\n\nLATEST USER MESSAGE:\n"
        + latest_user_message
    )

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.25,
            max_output_tokens=_response_budget(latest_user_message),
            response_mime_type="application/json",
        ),
    )

    raw_text = getattr(response, "text", None)

    if not raw_text:
        raise RuntimeError(
            "The research assistant returned an empty response."
        )

    result = json.loads(raw_text)

    intent = result.get("intent")

    if intent not in ALLOWED_INTENTS:
        raise ValueError(
            "The research assistant returned an invalid intent."
        )

    assistant_text = str(result.get("response", "")).strip()

    if not assistant_text:
        raise RuntimeError(
            "The research assistant returned an empty answer."
        )

    result["response"] = assistant_text
    result["needs_follow_up"] = bool(
        result.get("needs_follow_up", False)
    )
    result["follow_up_question"] = str(
        result.get("follow_up_question", "")
    )
    result["research_question"] = str(
        result.get("research_question", "")
    )
    result["hypothesis"] = str(
        result.get("hypothesis", "")
    )

    action = result.get("research_action")

    if intent == "propose_experiment":
        if action not in ALLOWED_RESEARCH_ACTIONS:
            action = "ambiguous"
    else:
        action = None

    result["research_action"] = action

    reference = result.get("referenced_experiment_id")
    result["referenced_experiment_id"] = (
        str(reference).strip() if reference else None
    )

    usage_metadata = getattr(response, "usage_metadata", None)

    usage = {
        "provider": "gemini",
        "model": model,
        "input_tokens": getattr(
            usage_metadata, "prompt_token_count", 0
        ) or 0,
        "output_tokens": getattr(
            usage_metadata, "candidates_token_count", 0
        ) or 0,
        "total_tokens": getattr(
            usage_metadata, "total_token_count", 0
        ) or 0,
    }

    return result, usage


def _persist_langgraph_proposal(
    *,
    session_id: UUID,
    routing: dict,
    workflow_result: dict,
) -> dict:
    """
    Persist a LangGraph proposal in the same format used by the
    existing Agent 2 approval and execution endpoints.

    This function never approves or executes an experiment.
    """

    workflow_status = workflow_result.get("status")

    if workflow_status == "needs_clarification":
        return {
            "status": "needs_clarification",
            "assistant_message": workflow_result.get(
                "assistant_message",
                "I need one clarification before designing this experiment.",
            ),
            "agent_run_id": None,
            "ledger_id": None,
        }

    if workflow_status == "validation_failed":
        errors = workflow_result.get("validation_errors") or []

        error_text = "\n".join(
            f"- {error}" for error in errors
        )

        message = (
            workflow_result.get("assistant_message")
            or "The proposed configuration did not pass validation."
        )

        if error_text:
            message += "\n\nValidation details:\n" + error_text

        return {
            "status": "validation_failed",
            "assistant_message": message,
            "agent_run_id": None,
            "ledger_id": None,
        }

    if workflow_status != "proposal_validated":
        raise RuntimeError(
            "Unexpected LangGraph workflow status: "
            f"{workflow_status}"
        )

    # Validate compatibility with the existing approval pipeline.
    # This is a schema validation only; no experiment is executed.
    proposal = Agent2Proposal.model_validate({
        "research_question": workflow_result.get("research_question", ""),
        "hypothesis": workflow_result.get("hypothesis", ""),
        "rationale": workflow_result.get("rationale", ""),
        "expected_learning": workflow_result.get("expected_learning", ""),
        "experiment_type": workflow_result.get("experiment_type"),
        "confidence": workflow_result.get("confidence", "medium"),
        "research_request": workflow_result.get("validated_request"),
        "parent_experiment_id": routing.get(
            "referenced_experiment_id"
        ),
    })

    proposal_data = proposal.model_dump(mode="json")
    usage = workflow_result.get("usage") or {}

    run_id = str(uuid4())
    now = _now()
    db = get_supabase_client()

    # Create the durable agent-run record.
    db.table("agent_runs").insert({
        "id": run_id,
        "session_id": str(session_id),
        "thread_id": str(session_id),
        "status": "running",
        "current_step": "saving_proposal",
        "provider": usage.get("provider", "gemini"),
        "model": usage.get("model"),
        "tokens_used": int(usage.get("total_tokens") or 0),
        "input_data": {
            "research_question": proposal.research_question,
            "hypothesis": proposal.hypothesis,
            "design_mode": (
                "follow_up"
                if routing.get("research_action") == "follow_up"
                else "initial"
            ),
            "referenced_experiment_id": routing.get(
                "referenced_experiment_id"
            ),
        },
        "output_data": {
            "proposal": proposal_data,
            "usage": usage,
            "workflow": "langgraph",
        },
        "started_at": now,
    }).execute()

    # Persist in the same ledger shape used by the existing
    # /propose endpoint.
    ledger_response = (
        db.table("research_ledger")
        .insert({
            "session_id": str(session_id),
            "agent_run_id": run_id,
            "hypothesis": proposal.hypothesis,
            "hypothesis_family": None,
            "status": "proposed",
            "approval_status": "pending",
            "proposal": proposal_data,
            "decision": {},
            "evidence_summary": {},
        })
        .execute()
    )

    ledger_rows = ledger_response.data or []

    if not ledger_rows:
        db.table("agent_runs").update({
            "status": "failed",
            "current_step": "ledger_persistence_failed",
            "updated_at": _now(),
        }).eq("id", run_id).execute()

        raise RuntimeError(
            "The proposal could not be saved to the research ledger."
        )

    ledger = ledger_rows[0]

    # Mark the run as awaiting approval. The approval endpoint
    # will later queue it using the existing execution pipeline.
    db.table("agent_runs").update({
        "status": "awaiting_approval",
        "current_step": "awaiting_human_approval",
        "completed_at": _now(),
        "updated_at": _now(),
    }).eq("id", run_id).execute()

    assistant_text = (
        f"Experiment proposal: {proposal.research_question}\n\n"
        f"Hypothesis: {proposal.hypothesis}\n\n"
        f"Rationale: {proposal.rationale}\n\n"
        f"Expected learning: {proposal.expected_learning}\n\n"
        f"Design details: {workflow_result.get('assistant_message', '')}\n\n"
        "The proposed configuration passed deterministic validation. "
        "It has NOT been executed. Explicit approval is required."
    )

    return {
        "status": "proposal_saved",
        "assistant_message": assistant_text,
        "agent_run_id": run_id,
        "ledger_id": ledger["id"],
        "proposal": proposal_data,
    }


@router.post("/sessions/{session_id}/chat")
def chat_with_research_assistant(
    session_id: UUID,
    request: ChatMessageRequest,
) -> dict:

    _get_active_session(session_id)

    db = get_supabase_client()
    message = request.message.strip()

    try:
        existing = (
            db.table("chat_messages")
            .select("id")
            .eq("session_id", str(session_id))
            .eq("role", "user")
            .contains(
                "metadata",
                {"client_message_id": request.client_message_id},
            )
            .limit(1)
            .execute()
        )

        if not existing.data:
            db.table("chat_messages").insert({
                "session_id": str(session_id),
                "role": "user",
                "content": message,
                "metadata": {
                    "client_message_id": request.client_message_id,
                },
            }).execute()

        messages = _load_recent_messages(session_id)
        available_experiments = _load_session_experiments(session_id)

        routed, router_usage = _call_research_router(
            messages,
            message,
            available_experiments,
        )

        routing = {
            "research_action": None,
            "referenced_experiment_id": None,
            "prior_research_request": None,
            "evidence_summary": None,
            "clarification_question": None,
        }

        workflow_status = None
        agent_run_id = None
        ledger_id = None

        assistant_text = routed["response"]
        needs_follow_up = routed["needs_follow_up"]
        follow_up_question = routed["follow_up_question"]

        response_usage = {
            "router": router_usage,
            "designer": None,
        }

        # --------------------------------------------------------
        # Proposal intent: resolve initial vs follow-up first.
        # --------------------------------------------------------

        if routed["intent"] == "propose_experiment":

            routing = resolve_research_action(
                classifier_action=routed["research_action"],
                referenced_experiment_id=(
                    routed["referenced_experiment_id"]
                ),
                experiments=available_experiments,
            )

            if routing["research_action"] == "clarification_required":
                assistant_text = routing["clarification_question"]
                needs_follow_up = True
                follow_up_question = assistant_text

            else:
                workflow_kwargs = {
                    "session_id": str(session_id),
                    "user_message": message,
                    "conversation_history": messages,
                }

                # ------------------------------------------------
                # LangGraph initial or follow-up design.
                # ------------------------------------------------

                if routing["research_action"] == "follow_up":
                    workflow_result = run_follow_up_research_design(
                        **workflow_kwargs,
                        prior_research_request=(
                            routing["prior_research_request"]
                        ),
                        evidence_summary=routing["evidence_summary"],
                        previous_experiment_id=(
                            routing["referenced_experiment_id"]
                        ),
                    )

                elif routing["research_action"] == "new_research":
                    workflow_result = run_initial_research_design(
                        **workflow_kwargs,
                    )

                else:
                    raise RuntimeError(
                        "Research action was not resolved before "
                        "invoking LangGraph."
                    )

                response_usage["designer"] = (
                    workflow_result.get("usage") or {}
                )

                persisted = _persist_langgraph_proposal(
                    session_id=session_id,
                    routing=routing,
                    workflow_result=workflow_result,
                )

                workflow_status = persisted["status"]
                assistant_text = persisted["assistant_message"]
                agent_run_id = persisted.get("agent_run_id")
                ledger_id = persisted.get("ledger_id")

                if workflow_status == "needs_clarification":
                    needs_follow_up = True
                    follow_up_question = assistant_text

                elif workflow_status == "validation_failed":
                    needs_follow_up = True
                    follow_up_question = ""

                else:
                    needs_follow_up = False
                    follow_up_question = ""

        # --------------------------------------------------------
        # Persist the assistant message exactly once.
        # --------------------------------------------------------

        metadata = {
            "intent": routed["intent"],
            "needs_follow_up": needs_follow_up,
            "follow_up_question": follow_up_question,
            "research_question": routed["research_question"],
            "hypothesis": routed["hypothesis"],
            "research_action": routing["research_action"],
            "referenced_experiment_id": (
                routing["referenced_experiment_id"]
            ),
            "workflow_status": workflow_status,
            "agent_run_id": agent_run_id,
            "ledger_id": ledger_id,
            "usage": response_usage,
        }

        db.table("chat_messages").insert({
            "session_id": str(session_id),
            "role": "assistant",
            "content": assistant_text,
            "metadata": metadata,
        }).execute()

        db.table("chat_sessions").update({
            "updated_at": _now(),
        }).eq("id", str(session_id)).execute()

        return {
            "success": True,
            "session_id": str(session_id),
            "intent": routed["intent"],
            "response": assistant_text,
            "needs_follow_up": needs_follow_up,
            "follow_up_question": follow_up_question,
            "research_question": routed["research_question"],
            "hypothesis": routed["hypothesis"],
            "research_action": routing["research_action"],
            "referenced_experiment_id": (
                routing["referenced_experiment_id"]
            ),
            "workflow_status": workflow_status,
            "agent_run_id": agent_run_id,
            "ledger_id": ledger_id,
            "usage": response_usage,
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Conversational research request failed."
        )

        error_text = str(exc).lower()

        if "billing" in error_text or "outstanding balance" in error_text:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "AI_PROVIDER_BILLING",
                    "message": (
                        "The Gemini billing account needs attention. "
                        "Your message has been saved; you can retry "
                        "after restoring provider access."
                    ),
                },
            ) from exc

        if "429" in error_text or "resource_exhausted" in error_text:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "AI_PROVIDER_LIMIT",
                    "message": (
                        "The AI provider rate limit was reached. "
                        "Your message has been saved. Please retry shortly."
                    ),
                },
            ) from exc

        raise HTTPException(
            status_code=502,
            detail={
                "code": "AI_PROVIDER_ERROR",
                "message": (
                    "The research assistant could not complete this "
                    "response. Your message has been saved; please retry."
                ),
            },
        ) from exc
