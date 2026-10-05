
from __future__ import annotations

# -*- coding: utf-8 -*-
"""
Created on Mon Oct  5 13:43:52 2026

@author: mohak
"""

"""
FastAPI routes for Research Agent 2.

Agent 2 proposes exactly one controlled research experiment.
The deterministic Research Engine remains responsible for
actually executing that experiment.
"""

from fastapi import APIRouter, HTTPException

from api.research_agent.agent import (
    propose_next_experiment,
)
from api.research_agent.guardrails import (
    Agent2GuardrailError,
    validate_agent_2_proposal,
)
from api.research_agent.models import (
    Agent2Request,
)


router = APIRouter(
    prefix="/agent/research",
    tags=["research-agent"],
)


@router.post("/suggest")
def suggest_next_experiment(
    request: Agent2Request,
) -> dict:
    """
    Ask Agent 2 for exactly one next research experiment.

    Flow:

        Research context
            ->
        LLM proposal
            ->
        deterministic guardrails
            ->
        validated proposal
    """

    try:
        response = propose_next_experiment(
            request
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Research Agent could not generate "
                f"a proposal: {exc}"
            ),
        ) from exc

    try:
        validated_proposal = validate_agent_2_proposal(
            request,
            response.proposal,
        )

    except Agent2GuardrailError as exc:
        raise HTTPException(
            status_code=422,
            detail=(
                "Research Agent proposal rejected "
                f"by deterministic guardrails: {exc}"
            ),
        ) from exc

    return {
        "success": True,
        "proposal": validated_proposal.model_dump(
            mode="json"
        ),
        "model": response.model,
        "usage": response.usage,
    }