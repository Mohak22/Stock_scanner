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
    Small semantic proposal produced by the LLM.

    The LLM does NOT construct a ResearchRequest.

    Python deterministically converts this proposal into
    a ResearchRequest afterwards.
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

    # ==============================================================
    # THRESHOLD SENSITIVITY
    # ==============================================================

    # Exact feature whose threshold should be changed.
    #
    # Example:
    #     RSI(14) < 30
    #
    # target_feature = "rsi"
    target_feature: str | None = None

    # Optional period used to identify the exact feature instance.
    #
    # Example:
    #     RSI(14)
    #
    # target_period = 14
    target_period: int | None = None

    # New threshold value.
    threshold_value: float | None = None

    # Comparison operator for the proposed condition.
    threshold_operator: Literal[
        ">",
        ">=",
        "<",
        "<=",
    ] | None = None

    # ==============================================================
    # HORIZON
    # ==============================================================

    horizons: list[int] | None = None

    # ==============================================================
    # CONFIRMATION VARIABLES
    # ==============================================================

    confirmation_feature: str | None = None

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

        # ----------------------------------------------------------
        # Threshold sensitivity
        # ----------------------------------------------------------

        if self.experiment_type == "threshold_sensitivity":

            if not self.target_feature:
                raise ValueError(
                    "threshold_sensitivity requires "
                    "target_feature."
                )

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

            if self.target_period is not None:
                if self.target_period <= 0:
                    raise ValueError(
                        "target_period must be positive."
                    )

        # ----------------------------------------------------------
        # Horizon
        # ----------------------------------------------------------

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

        # ----------------------------------------------------------
        # Confirmation
        # ----------------------------------------------------------

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