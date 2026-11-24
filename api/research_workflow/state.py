
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 23 17:35:59 2026

@author: mohak
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class ResearchWorkflowState(TypedDict, total=False):
    """State carried between LangGraph nodes."""

    session_id: str
    design_mode: Literal["initial", "follow_up"]

    user_message: str
    conversation_history: list[dict[str, str]]

    # Follow-up context: compact, factual evidence only.
    prior_research_request: dict[str, Any] | None
    evidence_summary: dict[str, Any] | None
    previous_experiment_id: str | None

    status: Literal[
        "started",
        "needs_clarification",
        "proposal_generated",
        "validation_failed",
        "proposal_validated",
    ]

    assistant_message: str
    research_question: str
    hypothesis: str
    rationale: str
    expected_learning: str
    experiment_type: str
    confidence: str

    proposed_request: dict[str, Any] | None
    validated_request: dict[str, Any] | None

    validation_errors: list[str]
    usage: dict[str, Any]
