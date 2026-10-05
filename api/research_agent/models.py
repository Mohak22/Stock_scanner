# -*- coding: utf-8 -*-
"""
Created on Sun Oct  4 15:34:00 2026

@author: mohak
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from api.research.models import ResearchRequest


ExperimentType = Literal[
    "threshold_sensitivity",
    "confirmation_variable",
    "delivery_confirmation",
    "market_regime",
    "horizon",
    "robustness",
    "feature_interaction",
]


class ExperimentHistoryItem(BaseModel):
    experiment_id: str | None = None
    parent_experiment_id: str | None = None
    status: Literal["SAVED", "LOCKED"] | str = "SAVED"
    research_question: str | None = None
    hypothesis: str | None = None
    experiment_type: str | None = None
    research_request: dict[str, Any] | None = None
    research_result: dict[str, Any] | None = None


class Agent2Request(BaseModel):
    research_question: str = Field(min_length=1)
    hypothesis: str = Field(min_length=1)
    base_research_request: ResearchRequest
    latest_result: dict[str, Any] = Field(default_factory=dict)
    experiment_history: list[ExperimentHistoryItem] = Field(
        default_factory=list
    )


class Agent2SemanticProposal(BaseModel):
    """
    Small proposal schema given to the LLM.

    IMPORTANT:
    The LLM does NOT construct ResearchRequest directly.

    Python converts this semantic proposal into a
    deterministic ResearchRequest afterwards.
    """

    research_question: str = Field(min_length=1)
    hypothesis: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    expected_learning: str = Field(min_length=1)

    experiment_type: ExperimentType

    confidence: Literal[
        "low",
        "medium",
        "high",
    ] = "medium"

    # Used for threshold_sensitivity.
    threshold_value: float | None = None

    # Used for threshold_sensitivity.
    threshold_operator: Literal[
        ">",
        ">=",
        "<",
        "<=",
    ] | None = None

    # Used for horizon experiments.
    horizons: list[int] | None = None

    # Used for confirmation_variable /
    # delivery_confirmation.
    confirmation_feature: str | None = None

    # Used when the confirmation feature requires
    # a period, e.g. average_volume(20).
    confirmation_period: int | None = None

    @model_validator(mode="after")
    def validate_semantic_proposal(
        self,
    ) -> "Agent2SemanticProposal":

        if not self.research_question.strip():
            raise ValueError(
                "research_question cannot be empty."
            )

        if not self.hypothesis.strip():
            raise ValueError(
                "hypothesis cannot be empty."
            )

        if not self.rationale.strip():
            raise ValueError(
                "rationale cannot be empty."
            )

        if not self.expected_learning.strip():
            raise ValueError(
                "expected_learning cannot be empty."
            )

        if (
            self.experiment_type
            == "threshold_sensitivity"
        ):
            if self.threshold_value is None:
                raise ValueError(
                    "threshold_sensitivity requires "
                    "threshold_value."
                )

            if self.threshold_operator is None:
                raise ValueError(
                    "threshold_sensitivity requires "
                    "threshold_operator."
                )

        if self.experiment_type == "horizon":
            if not self.horizons:
                raise ValueError(
                    "horizon experiment requires "
                    "at least one horizon."
                )

            if any(
                horizon <= 0
                for horizon in self.horizons
            ):
                raise ValueError(
                    "All horizons must be positive."
                )

        if self.experiment_type in {
            "confirmation_variable",
            "delivery_confirmation",
        }:
            if not self.confirmation_feature:
                raise ValueError(
                    "Confirmation experiments require "
                    "confirmation_feature."
                )

        return self


class Agent2Proposal(BaseModel):
    """
    Final validated Agent 2 proposal.

    This is what the rest of the application receives.

    Unlike Agent2SemanticProposal, this contains the
    complete deterministic ResearchRequest.
    """

    research_question: str = Field(min_length=1)
    hypothesis: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    expected_learning: str = Field(min_length=1)

    experiment_type: ExperimentType

    confidence: Literal[
        "low",
        "medium",
        "high",
    ] = "medium"

    research_request: ResearchRequest

    parent_experiment_id: str | None = None

    @model_validator(mode="after")
    def validate_proposal(
        self,
    ) -> "Agent2Proposal":

        if not self.research_question.strip():
            raise ValueError(
                "research_question cannot be empty."
            )

        if not self.hypothesis.strip():
            raise ValueError(
                "hypothesis cannot be empty."
            )

        if not self.rationale.strip():
            raise ValueError(
                "rationale cannot be empty."
            )

        if not self.expected_learning.strip():
            raise ValueError(
                "expected_learning cannot be empty."
            )

        return self


class Agent2Response(BaseModel):
    proposal: Agent2Proposal
    model: str
    usage: dict[str, Any] = Field(
        default_factory=dict
    )