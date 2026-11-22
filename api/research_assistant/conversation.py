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
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.integrations.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter()

class ChatMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)

ALLOWED_INTENTS = {
    "research_question",
    "propose_experiment",
    "explain_experiment",
    "compare_experiments",
    "out_of_scope",
    "needs_clarification",
}

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

def _load_recent_messages(session_id: UUID, limit: int = 12) -> list[dict]:
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

def _call_research_router(messages: list[dict]) -> tuple[dict, dict]:
    """
    One LLM call classifies the user's intent and drafts the response.
    The LLM cannot execute research or invent engine results.
    """
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

    system_prompt = """
You are the conversational research assistant for a stock research
and experimentation platform.

Your job is to understand what the user actually wants and respond
appropriately. Do not force every message into an experiment.

Supported capabilities in this version:
- Explain stock-market, investing, statistics and research concepts.
- Discuss the user's existing research experiments when evidence
  is present in the conversation.
- Understand and refine research hypotheses.
- Identify requests that could become experiments.
- Ask concise follow-up questions when essential information is missing.

Not available yet:
- Live web search, current news, quarterly-result retrieval,
  live market sentiment or real-time prices.
- Executing a new experiment directly from this chat.
- Access to evidence or files that have not been supplied to you.

Rules:
1. Never invent stock prices, news, financial results, experiment
   results, statistics or data.
2. If the user asks for current news, results or sentiment, clearly
   explain that web search is not connected yet. Do not fabricate
   an answer.
3. If a request is unrelated to stock research, markets, investing,
   statistics or this product, politely state the assistant's scope.
4. If the user wants an experiment, identify the research question
   and hypothesis. Ask only for information essential to proceed.
5. Use conversation history to resolve references such as "that
   experiment", "it", "the previous result" and follow-up answers.
6. If the user is only asking a conceptual question, answer it
   directly. Do not ask unnecessary questions.
7. Be transparent about limitations and uncertainty.
8. Keep responses concise, practical and conversational.

Return a JSON object with exactly these keys:
{
  "intent": one of the allowed intent values,
  "response": "The message shown to the user",
  "needs_follow_up": true or false,
  "follow_up_question": "One concise question, or empty string",
  "research_question": "A concise research question if applicable, else empty",
  "hypothesis": "A testable hypothesis if applicable, else empty"
}

Allowed intent values:
research_question, propose_experiment, explain_experiment,
compare_experiments, out_of_scope, needs_clarification

Important:
- A proposed experiment is only an identified research idea.
  Do not claim that it has been configured, approved or executed.
- Do not output markdown fences or text outside the JSON object.
"""

    prompt = (
        system_prompt
        + "\n\nCONVERSATION HISTORY:\n"
        + json.dumps(messages, ensure_ascii=False, default=str)
    )

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=650,
            response_mime_type="application/json",
        ),
    )

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise RuntimeError("The research router returned an empty response.")

    result = json.loads(raw_text)

    intent = result.get("intent")
    if intent not in ALLOWED_INTENTS:
        raise ValueError(f"Unsupported router intent: {intent}")

    result.setdefault("response", "")
    result.setdefault("needs_follow_up", False)
    result.setdefault("follow_up_question", "")
    result.setdefault("research_question", "")
    result.setdefault("hypothesis", "")

    usage_metadata = getattr(response, "usage_metadata", None)
    usage = {
        "provider": "gemini",
        "model": model,
        "input_tokens": getattr(usage_metadata, "prompt_token_count", 0) or 0,
        "output_tokens": getattr(usage_metadata, "candidates_token_count", 0) or 0,
        "total_tokens": getattr(usage_metadata, "total_token_count", 0) or 0,
    }

    return result, usage

@router.post("/sessions/{session_id}/chat")
def chat_with_research_assistant(
    session_id: UUID,
    request: ChatMessageRequest,
) -> dict:
    _get_active_session(session_id)
    db = get_supabase_client()

    try:
        # Save the user's message first.
        db.table("chat_messages").insert({
            "session_id": str(session_id),
            "role": "user",
            "content": request.message.strip(),
            "metadata": {},
        }).execute()

        # Include the latest message and recent conversational context.
        messages = _load_recent_messages(session_id)

        routed, usage = _call_research_router(messages)

        assistant_text = str(routed.get("response", "")).strip()
        if not assistant_text:
            raise RuntimeError("The research router produced no user response.")

        # Persist assistant response and routing metadata.
        db.table("chat_messages").insert({
            "session_id": str(session_id),
            "role": "assistant",
            "content": assistant_text,
            "metadata": {
                "intent": routed["intent"],
                "needs_follow_up": bool(routed["needs_follow_up"]),
                "follow_up_question": routed["follow_up_question"],
                "research_question": routed["research_question"],
                "hypothesis": routed["hypothesis"],
                "usage": usage,
            },
        }).execute()

        db.table("chat_sessions").update({
            "updated_at": _now(),
        }).eq("id", str(session_id)).execute()

        return {
            "success": True,
            "session_id": str(session_id),
            "intent": routed["intent"],
            "response": assistant_text,
            "needs_follow_up": bool(routed["needs_follow_up"]),
            "follow_up_question": routed["follow_up_question"],
            "research_question": routed["research_question"],
            "hypothesis": routed["hypothesis"],
            "usage": usage,
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Conversational research routing failed.")
        raise HTTPException(
            status_code=502,
            detail=f"Could not process chat message: {type(exc).__name__}: {exc}",
        ) from exc