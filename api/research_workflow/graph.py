
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Created on Mon Nov 23 17:34:43 2026

@author: mohak
"""

from typing import Any, Callable, Literal

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from api.research.models import ResearchRequest
from api.research_workflow.designer import (
    ResearchDesignerOutput,
    design_experiment,
)
from api.research_workflow.state import ResearchWorkflowState


DesignerFunction = Callable[..., tuple[
    ResearchDesignerOutput,
    dict[str, Any],
]]


def create_research_designer_node(designer_function: DesignerFunction):
    def research_designer_node(state: ResearchWorkflowState) -> dict[str, Any]:
        result, usage = designer_function(
            user_message=state["user_message"],
            conversation_history=state.get("conversation_history", []),
            design_mode=state.get("design_mode", "initial"),
            prior_research_request=state.get("prior_research_request"),
            evidence_summary=state.get("evidence_summary"),
            previous_experiment_id=state.get("previous_experiment_id"),
            previous_ledger_id=state.get("previous_ledger_id"),
        )

        common = {
            "assistant_message": result.assistant_message,
            "research_question": result.research_question,
            "hypothesis": result.hypothesis,
            "rationale": result.rationale,
            "expected_learning": result.expected_learning,
            "experiment_type": result.experiment_type,
            "confidence": result.confidence,
            "usage": usage,
        }

        if result.status == "needs_clarification":
            return {
                **common,
                "status": "needs_clarification",
                "proposed_request": None,
                "validated_request": None,
                "validation_errors": [],
            }

        return {
            **common,
            "status": "proposal_generated",
            "proposed_request": result.research_request,
            "validated_request": None,
            "validation_errors": [],
        }

    return research_designer_node


def validate_research_request_node(state: ResearchWorkflowState) -> dict[str, Any]:
    proposed_request = state.get("proposed_request")

    if not proposed_request:
        return {
            "status": "validation_failed",
            "validation_errors": ["The designer did not provide a research request."],
            "validated_request": None,
        }

    try:
        validated = ResearchRequest.model_validate(proposed_request)
        normalized = validated.model_dump(mode="json")

        return {
            "status": "proposal_validated",
            "validated_request": normalized,
            "validation_errors": [],
            "assistant_message": (
                state.get("assistant_message", "")
                + "\n\nThe proposed configuration passed deterministic "
                "validation. It has NOT been approved or executed."
            ),
        }

    except ValidationError as exc:
        errors = [
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        ]
        return {
            "status": "validation_failed",
            "validated_request": None,
            "validation_errors": errors,
            "assistant_message": (
                "The proposed configuration did not pass validation. "
                "No experiment was run."
            ),
        }

    except Exception as exc:
        return {
            "status": "validation_failed",
            "validated_request": None,
            "validation_errors": [str(exc)],
            "assistant_message": (
                "The proposed configuration could not be validated. "
                "No experiment was run."
            ),
        }


def route_after_design(state: ResearchWorkflowState) -> str:
    return "validate_request" if state.get("status") == "proposal_generated" else END


def build_research_graph(
    designer_function: DesignerFunction = design_experiment,
):
    builder = StateGraph(ResearchWorkflowState)

    builder.add_node(
        "research_designer",
        create_research_designer_node(designer_function),
    )
    builder.add_node("validate_request", validate_research_request_node)

    builder.add_edge(START, "research_designer")
    builder.add_conditional_edges(
        "research_designer",
        route_after_design,
        {"validate_request": "validate_request", END: END},
    )
    builder.add_edge("validate_request", END)

    return builder.compile()


def _run_design(
    *,
    session_id: str,
    user_message: str,
    design_mode: Literal["initial", "revision", "follow_up"],
    conversation_history: list[dict[str, str]] | None = None,
    prior_research_request: dict[str, Any] | None = None,
    evidence_summary: dict[str, Any] | None = None,
    previous_experiment_id: str | None = None,
    previous_ledger_id: str | None = None,
    designer_function: DesignerFunction = design_experiment,
) -> dict[str, Any]:

    if design_mode in {"revision", "follow_up"} and not prior_research_request:
        raise ValueError("A revision or follow-up requires the previous ResearchRequest.")

    if design_mode == "follow_up" and not evidence_summary:
        raise ValueError("A follow-up requires completed research evidence.")

    graph = build_research_graph(designer_function)

    initial_state: ResearchWorkflowState = {
        "session_id": session_id,
        "design_mode": design_mode,
        "user_message": user_message,
        "conversation_history": conversation_history or [],
        "prior_research_request": prior_research_request,
        "evidence_summary": evidence_summary,
        "previous_experiment_id": previous_experiment_id,
        "previous_ledger_id": previous_ledger_id,
        "status": "started",
        "validation_errors": [],
    }

    return graph.invoke(initial_state)


def run_initial_research_design(**kwargs):
    return _run_design(design_mode="initial", **kwargs)


def run_revision_research_design(**kwargs):
    return _run_design(design_mode="revision", **kwargs)


def run_follow_up_research_design(**kwargs):
    return _run_design(design_mode="follow_up", **kwargs)
