
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
    run_revision_research_design,
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
    "revise_proposal",
    "follow_up",
    "ambiguous",
}


class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    client_message_id: str = Field(min_length=8, max_length=100)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_saved_chat_response(
    *,
    session_id: UUID,
    content: str,
    metadata: dict,
) -> dict:
    """Reconstruct the original API response for an idempotent retry."""

    metadata = metadata or {}

    return {
        "success": True,
        "session_id": str(session_id),
        "intent": metadata.get("intent"),
        "response": content,
        "needs_follow_up": metadata.get("needs_follow_up", False),
        "follow_up_question": metadata.get("follow_up_question", ""),
        "research_question": metadata.get("research_question", ""),
        "hypothesis": metadata.get("hypothesis", ""),
        "research_action": metadata.get("research_action"),
        "design_mode": metadata.get("design_mode"),
        "referenced_experiment_id": metadata.get(
            "referenced_experiment_id"
        ),
        "referenced_ledger_id": metadata.get("referenced_ledger_id"),
        "workflow_status": metadata.get("workflow_status"),
        "agent_run_id": metadata.get("agent_run_id"),
        "ledger_id": metadata.get("ledger_id"),
        "usage": metadata.get("usage", {}),
    }


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
    """Load this session's experiment records and build compact context."""

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


def _find_explicit_reference(
    message: str,
    experiments: list[dict],
) -> str | None:
    """
    Prefer an exact ID mentioned by the user over the classifier's guess.
    Both Ledger IDs and Experiment IDs are accepted.
    """

    message_lower = message.lower()

    for item in experiments:
        for key in ("ledger_id", "experiment_id"):
            reference = item.get(key)

            if reference and str(reference).lower() in message_lower:
                return str(reference)

    return None


def _apply_deterministic_action_cues(
    *,
    message: str,
    action: str | None,
) -> str | None:
    """
    Apply clear language cues without overriding evidence-based follow-ups.
    The LLM remains responsible for interpreting less obvious requests.
    """

    text = message.lower()

    follow_up_cues = (
        "based on the results",
        "based on results",
        "according to the results",
        "based on its results",
        "follow-up",
        "follow up",
        "use the evidence",
        "using the evidence",
        "what did the results suggest",
        "extend the completed experiment",
    )

    revision_cues = (
        "revise",
        "revision",
        "modify",
        "change the",
        "update the",
        "adjust the",
        "keep everything else",
        "same settings",
        "same configuration",
        "replace the",
        "add a condition",
        "remove the filter",
    )

    new_research_cues = (
        "new independent experiment",
        "independent experiment",
        "completely new experiment",
        "different hypothesis",
        "start a new experiment",
    )

    if any(cue in text for cue in new_research_cues):
        return "new_research"

    if any(cue in text for cue in follow_up_cues):
        return "follow_up"

    if any(cue in text for cue in revision_cues):
        return "revise_proposal"

    return action


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
        os.getenv("RESEARCH_AGENT_MODEL", "gemini-3.5-flash-lite"),
    )

    client = genai.Client(api_key=api_key)

    experiment_references = [
        {
            "ledger_id": item.get("ledger_id"),
            "experiment_id": item.get("experiment_id"),
            "hypothesis": item.get("hypothesis", ""),
            "status": item.get("status", ""),
            "approval_status": item.get("approval_status", ""),
            "can_revise": item.get("can_revise", False),
            "can_follow_up": item.get("can_follow_up", False),
        }
        for item in (available_experiments or [])
    ]

    system_prompt = """
You are the conversational research assistant for Stock Scanner.

Help the user understand markets, statistics, hypotheses,
research methodology and the Stock Scanner platform.

You are a technical assistant, not a generic chatbot.

CAPABILITIES:
- Explain finance, statistics, probability and ML concepts.
- Discuss backtesting, temporal validation, leakage and research design.
- Help formulate and critique research hypotheses.
- Discuss saved experiments using only available saved context.

LIMITATIONS:
- Live web search and current market data are not connected.
- Do not claim to have executed an experiment from this chat.
- Do not invent experiment results, prices, financial figures or
  unsupported feature-engine capabilities.
- The deterministic Python research engine owns all calculations.

ANSWER QUALITY:
1. Answer the actual question first.
2. Explain intuition before terminology where useful.
3. Explain assumptions and limitations.
4. Ask one focused clarification only when essential.
5. Do not turn every question into an experiment.
6. Never invent capabilities or evidence.

INTENT CLASSIFICATION:
- research_question: conceptual or technical discussion.
- propose_experiment: the user wants an experiment proposal.
- explain_experiment: asks about an existing experiment.
- compare_experiments: wants experiments compared.
- out_of_scope: unrelated request.
- needs_clarification: essential information is missing.

For propose_experiment, classify research_action:

1. new_research:
   A new, independent experiment or different hypothesis.
   Previous experiments are not being used as the baseline.

2. revise_proposal:
   The user wants to change an existing proposal's configuration.
   This can apply to pending, rejected, failed or unapproved proposals.
   It does NOT require completed experiment evidence.
   Examples:
   - "Change the RSI threshold in the previous proposal."
   - "Keep everything else but add a volume filter."
   - "Revise proposal ledger-123."
   - "Use the same configuration but change the holding period."

3. follow_up:
   The user wants a new investigation informed by the results/evidence
   of a previously completed experiment.
   Follow-up requires completed, approved experiment evidence.
   Examples:
   - "Based on the results, test whether the effect holds in another regime."
   - "What do the results suggest we should investigate next?"

4. ambiguous:
   Use when the intended action or target cannot be identified.

IMPORTANT DISTINCTIONS:
- Revising a proposal is NOT the same as following up on results.
- A revision changes the proposed configuration; it does not use
  completed experiment evidence.
- A follow-up uses evidence from a completed, approved experiment.
- Do not classify every mention of a previous experiment as a revision.
- If the user clearly requests a new independent experiment, use
  new_research even if previous experiments exist.
- If the target of a revision or follow-up is unclear, use ambiguous.
- Never invent an ID. Only select IDs in AVAILABLE EXPERIMENTS.
- IDs may be Ledger IDs or Experiment IDs.
- For non-proposal intents, research_action and referenced_experiment_id
  must be null.

Return exactly these JSON keys:
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

A proposal is only a research idea. Do not claim it has been
configured, approved or executed.

Return valid JSON only. Do not use Markdown fences.
"""

    prompt = (
        system_prompt
        + "\n\nAVAILABLE EXPERIMENTS:\n"
        + json.dumps(experiment_references, ensure_ascii=False, default=str)
        + "\n\nRECENT CONVERSATION:\n"
        + json.dumps(messages, ensure_ascii=False, default=str)
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
        raise RuntimeError("The research assistant returned an empty response.")

    result = json.loads(raw_text)

    intent = result.get("intent")

    if intent not in ALLOWED_INTENTS:
        raise ValueError("The research assistant returned an invalid intent.")

    assistant_text = str(result.get("response", "")).strip()

    if not assistant_text:
        raise RuntimeError("The research assistant returned an empty answer.")

    result["response"] = assistant_text
    result["needs_follow_up"] = bool(result.get("needs_follow_up", False))
    result["follow_up_question"] = str(result.get("follow_up_question", ""))
    result["research_question"] = str(result.get("research_question", ""))
    result["hypothesis"] = str(result.get("hypothesis", ""))

    action = result.get("research_action")

    if intent == "propose_experiment":
        if action not in ALLOWED_RESEARCH_ACTIONS:
            action = "ambiguous"

        action = _apply_deterministic_action_cues(
            message=latest_user_message,
            action=action,
        )
    else:
        action = None

    result["research_action"] = action

    reference = result.get("referenced_experiment_id")
    reference = str(reference).strip() if reference else None

    explicit_reference = _find_explicit_reference(
        latest_user_message,
        available_experiments or [],
    )

    result["referenced_experiment_id"] = (
        explicit_reference or reference
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
    client_message_id: str,
    routing: dict,
    workflow_result: dict,
) -> dict:
    """Persist a validated proposal through the existing idempotent RPC."""

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
        error_text = "\n".join(f"- {error}" for error in errors)

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
            f"Unexpected LangGraph workflow status: {workflow_status}"
        )

    if not client_message_id:
        raise ValueError("client_message_id is required for persistence.")

    research_action = routing.get("research_action")

    # A revision is not a child experiment. Only an evidence-based
    # follow-up receives the previous experiment as its parent.
    parent_experiment_id = (
        routing.get("referenced_experiment_id")
        if research_action == "follow_up"
        else None
    )

    proposal = Agent2Proposal.model_validate({
        "research_question": workflow_result.get("research_question", ""),
        "hypothesis": workflow_result.get("hypothesis", ""),
        "rationale": workflow_result.get("rationale", ""),
        "expected_learning": workflow_result.get("expected_learning", ""),
        "experiment_type": workflow_result.get("experiment_type"),
        "confidence": workflow_result.get("confidence", "medium"),
        "research_request": workflow_result.get("validated_request"),
        "parent_experiment_id": parent_experiment_id,
    })

    proposal_data = proposal.model_dump(mode="json")
    usage = workflow_result.get("usage") or {}

    run_id = str(uuid4())
    now = _now()

    design_mode = {
        "new_research": "initial",
        "revise_proposal": "revision",
        "follow_up": "follow_up",
    }.get(research_action, "initial")

    input_data = {
        "research_question": proposal.research_question,
        "hypothesis": proposal.hypothesis,
        "design_mode": design_mode,
        "referenced_experiment_id": routing.get(
            "referenced_experiment_id"
        ),
        "referenced_ledger_id": routing.get("referenced_ledger_id"),
        "client_message_id": client_message_id,
    }

    output_data = {
        "proposal": proposal_data,
        "usage": usage,
        "workflow": "langgraph",
    }

    rpc_response = (
        get_supabase_client()
        .rpc(
            "persist_langgraph_proposal_idempotent",
            {
                "p_run_id": run_id,
                "p_session_id": str(session_id),
                "p_thread_id": str(session_id),
                "p_provider": usage.get("provider", "gemini"),
                "p_model": usage.get("model"),
                "p_tokens_used": int(usage.get("total_tokens") or 0),
                "p_input_data": input_data,
                "p_output_data": output_data,
                "p_started_at": now,
                "p_hypothesis": proposal.hypothesis,
                "p_proposal": proposal_data,
                "p_client_message_id": client_message_id,
            },
        )
        .execute()
    )

    result = rpc_response.data

    if isinstance(result, list) and result:
        result = result[0]

    if not isinstance(result, dict):
        raise RuntimeError(
            "The proposal persistence RPC returned an invalid response."
        )

    persisted_run_id = result.get("agent_run_id")
    ledger_id = result.get("ledger_id")

    if not persisted_run_id or not ledger_id:
        raise RuntimeError(
            "The proposal persistence RPC did not return both identifiers."
        )

    if design_mode == "revision":
        lead = (
            "Revised experiment proposal. The original proposal remains "
            "unchanged; this is a new proposal for your review."
        )
    elif design_mode == "follow_up":
        lead = "Follow-up experiment proposal based on the previous evidence."
    else:
        lead = "New experiment proposal."

    assistant_text = (
        f"{lead}\n\n"
        f"Research question: {proposal.research_question}\n\n"
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
        "agent_run_id": persisted_run_id,
        "ledger_id": ledger_id,
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
    client_message_id = request.client_message_id

    try:
        # 1. Check whether this user message was already received.
        existing_user = (
            db.table("chat_messages")
            .select("id,content")
            .eq("session_id", str(session_id))
            .eq("role", "user")
            .contains("metadata", {"client_message_id": client_message_id})
            .limit(1)
            .execute()
        )

        existing_user_rows = existing_user.data or []

        if existing_user_rows:
            saved_user = existing_user_rows[0]

            if saved_user["content"].strip() != message:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "IDEMPOTENCY_KEY_REUSED",
                        "message": (
                            "This client_message_id was already used "
                            "for a different message."
                        ),
                    },
                )
        else:
            try:
                db.table("chat_messages").insert({
                    "session_id": str(session_id),
                    "role": "user",
                    "content": message,
                    "metadata": {
                        "client_message_id": client_message_id,
                    },
                }).execute()

            except Exception:
                # A concurrent request may have inserted the message first.
                existing_user = (
                    db.table("chat_messages")
                    .select("id,content")
                    .eq("session_id", str(session_id))
                    .eq("role", "user")
                    .contains(
                        "metadata",
                        {"client_message_id": client_message_id},
                    )
                    .limit(1)
                    .execute()
                )

                rows = existing_user.data or []

                if not rows:
                    raise

                if rows[0]["content"].strip() != message:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "IDEMPOTENCY_KEY_REUSED",
                            "message": (
                                "This client_message_id was already used "
                                "for a different message."
                            ),
                        },
                    )

        # 2. Return an already completed response on retry.
        existing_assistant = (
            db.table("chat_messages")
            .select("content,metadata")
            .eq("session_id", str(session_id))
            .eq("role", "assistant")
            .contains("metadata", {"client_message_id": client_message_id})
            .limit(1)
            .execute()
        )

        assistant_rows = existing_assistant.data or []

        if assistant_rows:
            saved = assistant_rows[0]
            return _build_saved_chat_response(
                session_id=session_id,
                content=saved["content"],
                metadata=saved.get("metadata") or {},
            )

        # 3. Load context and invoke the conversational router.
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
            "referenced_ledger_id": None,
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

        # 4. Proposal intent: resolve new, revision or evidence follow-up.
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

                action = routing["research_action"]

                # 5. Invoke the correct LangGraph design mode.
                if action == "follow_up":
                    workflow_result = run_follow_up_research_design(
                        **workflow_kwargs,
                        prior_research_request=(
                            routing["prior_research_request"]
                        ),
                        evidence_summary=routing["evidence_summary"],
                        previous_experiment_id=(
                            routing["referenced_experiment_id"]
                        ),
                        previous_ledger_id=(
                            routing.get("referenced_ledger_id")
                        ),
                    )

                elif action == "revise_proposal":
                    workflow_result = run_revision_research_design(
                        **workflow_kwargs,
                        prior_research_request=(
                            routing["prior_research_request"]
                        ),
                        previous_experiment_id=(
                            routing.get("referenced_experiment_id")
                        ),
                        previous_ledger_id=(
                            routing.get("referenced_ledger_id")
                        ),
                    )

                elif action == "new_research":
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

                # 6. Persist the validated proposal idempotently.
                persisted = _persist_langgraph_proposal(
                    session_id=session_id,
                    client_message_id=client_message_id,
                    routing=routing,
                    workflow_result=workflow_result,
                )

                workflow_status = persisted["status"]
                assistant_text = persisted["assistant_message"]
                agent_run_id = persisted.get("agent_run_id")
                ledger_id = persisted.get("ledger_id")

                if workflow_status in {
                    "needs_clarification",
                    "validation_failed",
                }:
                    needs_follow_up = True
                    follow_up_question = (
                        assistant_text
                        if workflow_status == "needs_clarification"
                        else ""
                    )
                else:
                    needs_follow_up = False
                    follow_up_question = ""

        # 7. Persist assistant response with the same idempotency key.
        metadata = {
            "client_message_id": client_message_id,
            "intent": routed["intent"],
            "needs_follow_up": needs_follow_up,
            "follow_up_question": follow_up_question,
            "research_question": routed["research_question"],
            "hypothesis": routed["hypothesis"],
            "research_action": routing["research_action"],
            "design_mode": {
                "new_research": "initial",
                "revise_proposal": "revision",
                "follow_up": "follow_up",
            }.get(routing["research_action"]),
            "referenced_experiment_id": (
                routing.get("referenced_experiment_id")
            ),
            "referenced_ledger_id": routing.get("referenced_ledger_id"),
            "workflow_status": workflow_status,
            "agent_run_id": agent_run_id,
            "ledger_id": ledger_id,
            "usage": response_usage,
        }

        try:
            db.table("chat_messages").insert({
                "session_id": str(session_id),
                "role": "assistant",
                "content": assistant_text,
                "metadata": metadata,
            }).execute()

        except Exception:
            # A concurrent request may have completed this same message.
            existing_assistant = (
                db.table("chat_messages")
                .select("content,metadata")
                .eq("session_id", str(session_id))
                .eq("role", "assistant")
                .contains(
                    "metadata",
                    {"client_message_id": client_message_id},
                )
                .limit(1)
                .execute()
            )

            rows = existing_assistant.data or []

            if not rows:
                raise

            saved = rows[0]
            return _build_saved_chat_response(
                session_id=session_id,
                content=saved["content"],
                metadata=saved.get("metadata") or {},
            )

        db.table("chat_sessions").update({
            "updated_at": _now(),
        }).eq("id", str(session_id)).execute()

        # 8. Return API response.
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
            "design_mode": metadata["design_mode"],
            "referenced_experiment_id": (
                routing.get("referenced_experiment_id")
            ),
            "referenced_ledger_id": routing.get("referenced_ledger_id"),
            "workflow_status": workflow_status,
            "agent_run_id": agent_run_id,
            "ledger_id": ledger_id,
            "usage": response_usage,
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Conversational research request failed.")

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
