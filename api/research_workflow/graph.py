
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


def create_research_designer_node(
    designer_function: DesignerFunction,
):
    """LLM node for initial and follow-up experiment design."""

    def research_designer_node(
        state: ResearchWorkflowState,
    ) -> dict[str, Any]:

        result, usage = designer_function(
            user_message=state["user_message"],
            conversation_history=state.get("conversation_history", []),
            design_mode=state.get("design_mode", "initial"),
            prior_research_request=state.get("prior_research_request"),
            evidence_summary=state.get("evidence_summary"),
            previous_experiment_id=state.get("previous_experiment_id"),
        )

        common_output = {
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
                **common_output,
                "status": "needs_clarification",
                "proposed_request": None,
                "validated_request": None,
                "validation_errors": [],
            }

        return {
            **common_output,
            "status": "proposal_generated",
            "proposed_request": result.research_request,
            "validated_request": None,
            "validation_errors": [],
        }

    return research_designer_node


def validate_research_request_node(
    state: ResearchWorkflowState,
) -> dict[str, Any]:
    """Validate the candidate against the real ResearchRequest model."""

    proposed_request = state.get("proposed_request")

    if not proposed_request:
        return {
            "status": "validation_failed",
            "validation_errors": [
                "The designer did not provide a research request."
            ],
            "validated_request": None,
        }

    try:
        validated = ResearchRequest.model_validate(proposed_request)
        normalized_request = validated.model_dump(mode="json")

        return {
            "status": "proposal_validated",
            "validated_request": normalized_request,
            "validation_errors": [],
            "assistant_message": (
                state.get("assistant_message", "")
                + "\n\nThe proposed configuration passed "
                "deterministic validation. It has NOT been "
                "approved or executed."
            ),
        }

    except ValidationError as exc:
        errors = [
            (
                f"{'.'.join(str(part) for part in error['loc'])}: "
                f"{error['msg']}"
            )
            for error in exc.errors()
        ]

        return {
            "status": "validation_failed",
            "validated_request": None,
            "validation_errors": errors,
            "assistant_message": (
                "I drafted an experiment, but its configuration "
                "did not pass validation. No experiment was run."
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
    if state.get("status") == "proposal_generated":
        return "validate_request"

    return END


def build_research_graph(
    designer_function: DesignerFunction = design_experiment,
):
    """Build the reusable Research Designer graph."""

    builder = StateGraph(ResearchWorkflowState)

    builder.add_node(
        "research_designer",
        create_research_designer_node(designer_function),
    )
    builder.add_node(
        "validate_request",
        validate_research_request_node,
    )

    builder.add_edge(START, "research_designer")

    builder.add_conditional_edges(
        "research_designer",
        route_after_design,
        {
            "validate_request": "validate_request",
            END: END,
        },
    )

    builder.add_edge("validate_request", END)

    return builder.compile()


def _run_design(
    *,
    session_id: str,
    user_message: str,
    design_mode: Literal["initial", "follow_up"],
    conversation_history: list[dict[str, str]] | None = None,
    prior_research_request: dict[str, Any] | None = None,
    evidence_summary: dict[str, Any] | None = None,
    previous_experiment_id: str | None = None,
    designer_function: DesignerFunction = design_experiment,
) -> dict[str, Any]:

    if design_mode == "follow_up":
        if not prior_research_request:
            raise ValueError(
                "A follow-up design requires the previous ResearchRequest."
            )
        if not evidence_summary:
            raise ValueError(
                "A follow-up design requires an evidence summary."
            )

    graph = build_research_graph(designer_function)

    initial_state: ResearchWorkflowState = {
        "session_id": session_id,
        "design_mode": design_mode,
        "user_message": user_message,
        "conversation_history": conversation_history or [],
        "prior_research_request": prior_research_request,
        "evidence_summary": evidence_summary,
        "previous_experiment_id": previous_experiment_id,
        "status": "started",
        "validation_errors": [],
    }

    return graph.invoke(initial_state)


def run_initial_research_design(
    *,
    session_id: str,
    user_message: str,
    conversation_history: list[dict[str, str]] | None = None,
    designer_function: DesignerFunction = design_experiment,
) -> dict[str, Any]:
    """Design a new experiment from an initial research idea."""

    return _run_design(
        session_id=session_id,
        user_message=user_message,
        design_mode="initial",
        conversation_history=conversation_history,
        designer_function=designer_function,
    )


def run_follow_up_research_design(
    *,
    session_id: str,
    user_message: str,
    prior_research_request: dict[str, Any],
    evidence_summary: dict[str, Any],
    previous_experiment_id: str | None = None,
    conversation_history: list[dict[str, str]] | None = None,
    designer_function: DesignerFunction = design_experiment,
) -> dict[str, Any]:
    """
    Design an improvement experiment from a previous experiment's
    validated request and compact result evidence.
    """

    return _run_design(
        session_id=session_id,
        user_message=user_message,
        design_mode="follow_up",
        conversation_history=conversation_history,
        prior_research_request=prior_research_request,
        evidence_summary=evidence_summary,
        previous_experiment_id=previous_experiment_id,
        designer_function=designer_function,
    )
