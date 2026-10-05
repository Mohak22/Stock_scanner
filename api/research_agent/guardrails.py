
from __future__ import annotations

# -*- coding: utf-8 -*-
"""
Created on Mon Oct  5 13:32:24 2026

@author: mohak
"""

"""
Deterministic guardrails for Research Agent 2.

Agent 2 may propose experiments, but its proposals must pass through
this module before they can ever reach the deterministic Research Engine.

The philosophy is simple:

    LLM proposal
        ->
    deterministic validation
        ->
    allowed / rejected

The LLM is never trusted to enforce research governance by itself.
"""

from copy import deepcopy
from typing import Any

from pydantic import ValidationError

from api.research.features import get_feature_definition
from api.research_agent.models import (
    Agent2Proposal,
    Agent2Request,
)


# ======================================================================
# CONSTANTS
# ======================================================================

ALLOWED_EXPERIMENT_TYPES = {
    "threshold_sensitivity",
    "confirmation_variable",
    "delivery_confirmation",
    "market_regime",
    "horizon",
    "robustness",
    "feature_interaction",
}


# ======================================================================
# EXCEPTIONS
# ======================================================================

class Agent2GuardrailError(ValueError):
    """Raised when an Agent 2 proposal violates research governance."""


# ======================================================================
# BASIC HELPERS
# ======================================================================

def _normalise(value: Any) -> Any:
    """
    Convert Pydantic models into JSON-like dictionaries so that
    deterministic comparisons are easy.
    """

    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")

    if isinstance(value, dict):
        return {
            key: _normalise(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            _normalise(item)
            for item in value
        ]

    return value


def _feature_key(feature: dict) -> tuple:
    """
    Stable representation of a feature.
    """

    return (
        str(feature.get("type", "")).strip(),
        tuple(
            sorted(
                (
                    str(k),
                    str(v),
                )
                for k, v in (
                    feature.get("parameters") or {}
                ).items()
            )
        ),
    )


def _condition_key(condition: dict) -> tuple:
    """
    Stable representation of a condition.
    """

    return (
        _expression_key(
            condition.get("left") or {}
        ),
        condition.get("operator"),
        _expression_key(
            condition.get("right") or {}
        ),
    )


def _expression_key(expression: dict) -> tuple:
    """
    Stable representation of an expression.
    """

    if expression.get("feature") is not None:
        return (
            "feature",
            expression.get("feature"),
            tuple(
                sorted(
                    (
                        str(k),
                        str(v),
                    )
                    for k, v in (
                        expression.get("parameters")
                        or {}
                    ).items()
                )
            ),
            expression.get("multiplier", 1.0),
        )

    return (
        "value",
        expression.get("value"),
        expression.get("multiplier", 1.0),
    )


def _condition_signature_list(
    conditions: list[dict],
) -> list[tuple]:
    return [
        _condition_key(condition)
        for condition in conditions
    ]


def _feature_signature_list(
    features: list[dict],
) -> list[tuple]:
    return [
        _feature_key(feature)
        for feature in features
    ]


def _request_dump(request: Any) -> dict:
    return _normalise(
        request.model_dump(mode="json")
        if hasattr(request, "model_dump")
        else request
    )


# ======================================================================
# FEATURE VALIDATION
# ======================================================================

def validate_features(
    proposal_request: Any,
) -> None:
    """
    Ensure every proposed feature exists in the current registry.

    ResearchRequest already validates features through FeatureConfig,
    but this explicit guardrail gives Agent 2 a clear safety boundary.
    """

    for feature in proposal_request.features:
        feature_id = feature.type

        try:
            get_feature_definition(
                feature_id
            )
        except ValueError as exc:
            raise Agent2GuardrailError(
                f"Agent 2 proposed unsupported feature: "
                f"'{feature_id}'."
            ) from exc


# ======================================================================
# HOLDOUT GOVERNANCE
# ======================================================================

def validate_holdout_governance(
    request: Agent2Request,
    proposal: Agent2Proposal,
) -> None:
    """
    Prevent Agent 2 from iterating on final-holdout evidence.

    The final holdout is for final confirmation only.

    If the latest result contains final-holdout evidence, Agent 2 is
    not allowed to generate another proposal from that evidence.

    The existing holdout configuration must also remain unchanged.
    """

    base = _request_dump(
        request.base_research_request
    )

    proposed = _request_dump(
        proposal.research_request
    )

    latest_result = request.latest_result or {}

    final_holdout_result = latest_result.get(
        "final_holdout"
    )

    if final_holdout_result not in (
        None,
        {},
        [],
    ):
        raise Agent2GuardrailError(
            "Agent 2 cannot generate a new iterative experiment "
            "from final-holdout evidence. The final holdout is "
            "reserved for final confirmation."
        )

    base_holdout_start = base.get(
        "holdout_start"
    )
    base_holdout_end = base.get(
        "holdout_end"
    )

    proposed_holdout_start = proposed.get(
        "holdout_start"
    )
    proposed_holdout_end = proposed.get(
        "holdout_end"
    )

    if (
        base_holdout_start != proposed_holdout_start
        or base_holdout_end != proposed_holdout_end
    ):
        raise Agent2GuardrailError(
            "Agent 2 cannot modify the final-holdout period."
        )


# ======================================================================
# EXPERIMENT HISTORY
# ======================================================================

def validate_not_duplicate(
    request: Agent2Request,
    proposal: Agent2Proposal,
) -> None:
    """
    Prevent an exact duplicate of a previous experiment.
    """

    proposed_request = _request_dump(
        proposal.research_request
    )

    for history_item in request.experiment_history:

        previous_request = history_item.research_request

        if not previous_request:
            continue

        previous_request = _normalise(
            previous_request
        )

        if previous_request == proposed_request:
            previous_id = (
                history_item.experiment_id
                or "previous experiment"
            )

            raise Agent2GuardrailError(
                "Agent 2 proposed an exact duplicate of "
                f"{previous_id}."
            )


# ======================================================================
# PARENT LINEAGE
# ======================================================================

def validate_parent_lineage(
    request: Agent2Request,
    proposal: Agent2Proposal,
) -> None:
    """
    Ensure the proposed experiment points to the current experiment
    when an experiment ID is available.

    This keeps experiment lineage explicit.
    """

    if not request.experiment_history:
        return

    latest = request.experiment_history[0]

    latest_id = latest.experiment_id

    if not latest_id:
        return

    if proposal.parent_experiment_id is None:
        return

    if proposal.parent_experiment_id != latest_id:
        raise Agent2GuardrailError(
            "Agent 2 proposed an invalid parent_experiment_id. "
            f"Expected '{latest_id}', got "
            f"'{proposal.parent_experiment_id}'."
        )


# ======================================================================
# CONTROLLED-CHANGE VALIDATION
# ======================================================================

def _validate_common_configuration(
    base: dict,
    proposed: dict,
    *,
    experiment_type: str | None = None,
) -> None:
    protected_fields = {
        "universe",
        "development_start",
        "development_end",
        "validation_start",
        "validation_end",
        "holdout_start",
        "holdout_end",
        "signal_timing",
    }

    if experiment_type != "horizon":
        protected_fields.add("outcome_definition")

    for field in protected_fields:
        if base.get(field) != proposed.get(field):
            raise Agent2GuardrailError(
                "Agent 2 changed protected research configuration "
                f"field '{field}'. Controlled experiments must "
                "change only the variable being investigated."
            )

def _validate_threshold_experiment(
    base: dict,
    proposed: dict,
) -> None:
    """
    Threshold sensitivity:

        Return(1) > 7%
            ->
        Return(1) > 10%

    The condition structure should remain the same while a threshold
    changes.
    """

    base_conditions = base.get(
        "entry_conditions",
        [],
    )

    proposed_conditions = proposed.get(
        "entry_conditions",
        [],
    )

    if len(base_conditions) != len(proposed_conditions):
        raise Agent2GuardrailError(
            "Threshold sensitivity must preserve the number of "
            "entry conditions."
        )

    differences = 0

    for old, new in zip(
        base_conditions,
        proposed_conditions,
    ):

        old_left = old.get("left", {})
        new_left = new.get("left", {})

        old_right = old.get("right", {})
        new_right = new.get("right", {})

        # The operator must remain unchanged.
        if old.get("operator") != new.get("operator"):
            raise Agent2GuardrailError(
                "Threshold sensitivity cannot change the comparison "
                "operator."
            )

        # Left side must remain unchanged.
        if old_left != new_left:
            raise Agent2GuardrailError(
                "Threshold sensitivity cannot change the left-hand "
                "expression."
            )

        # The right side must remain the same expression type.
        old_right_feature = old_right.get(
            "feature"
        )
        new_right_feature = new_right.get(
            "feature"
        )

        if old_right_feature != new_right_feature:
            raise Agent2GuardrailError(
                "Threshold sensitivity cannot change the right-hand "
                "expression type."
            )

        old_parameters = old_right.get(
            "parameters",
            {},
        )

        new_parameters = new_right.get(
            "parameters",
            {},
        )

        if old_parameters != new_parameters:
            raise Agent2GuardrailError(
                "Threshold sensitivity cannot change feature parameters."
            )

        old_value = old_right.get("value")
        new_value = new_right.get("value")

        if old_value != new_value:
            differences += 1

        if old_right.get("multiplier", 1.0) != new_right.get(
            "multiplier",
            1.0,
        ):
            differences += 1

    if differences != 1:
        raise Agent2GuardrailError(
            "Threshold sensitivity must make exactly one threshold "
            "change."
        )


def _validate_horizon_experiment(
    base: dict,
    proposed: dict,
) -> None:
    base_evaluation_horizons = base.get(
        "evaluation_horizons",
        [],
    )

    proposed_evaluation_horizons = proposed.get(
        "evaluation_horizons",
        [],
    )

    if not proposed_evaluation_horizons:
        raise Agent2GuardrailError(
            "A horizon experiment must contain at least one horizon."
        )

    base_outcome_definition = base.get(
        "outcome_definition",
        {},
    )

    proposed_outcome_definition = proposed.get(
        "outcome_definition",
        {},
    )

    if not isinstance(
        base_outcome_definition,
        dict,
    ) or not isinstance(
        proposed_outcome_definition,
        dict,
    ):
        raise Agent2GuardrailError(
            "A horizon experiment requires a valid outcome_definition."
        )

    base_outcome_copy = dict(
        base_outcome_definition
    )
    proposed_outcome_copy = dict(
        proposed_outcome_definition
    )

    base_outcome_copy.pop(
        "horizons",
        None,
    )
    proposed_outcome_copy.pop(
        "horizons",
        None,
    )

    if base_outcome_copy != proposed_outcome_copy:
        raise Agent2GuardrailError(
            "A horizon experiment may change only "
            "'outcome_definition.horizons' inside "
            "the outcome definition."
        )

    proposed_outcome_horizons = proposed_outcome_definition.get(
        "horizons",
        [],
    )

    if proposed_evaluation_horizons != proposed_outcome_horizons:
        raise Agent2GuardrailError(
            "evaluation_horizons and "
            "outcome_definition.horizons must match."
        )

    base_without_horizon_fields = dict(base)
    proposed_without_horizon_fields = dict(proposed)

    base_without_horizon_fields.pop(
        "evaluation_horizons",
        None,
    )
    proposed_without_horizon_fields.pop(
        "evaluation_horizons",
        None,
    )

    base_outcome = dict(
        base_without_horizon_fields.get(
            "outcome_definition",
            {},
        )
    )
    proposed_outcome = dict(
        proposed_without_horizon_fields.get(
            "outcome_definition",
            {},
        )
    )

    base_outcome.pop(
        "horizons",
        None,
    )
    proposed_outcome.pop(
        "horizons",
        None,
    )

    base_without_horizon_fields[
        "outcome_definition"
    ] = base_outcome

    proposed_without_horizon_fields[
        "outcome_definition"
    ] = proposed_outcome

    if base_without_horizon_fields != proposed_without_horizon_fields:
        raise Agent2GuardrailError(
            "A horizon experiment may change only "
            "the evaluation horizons."
        )

def _validate_confirmation_experiment(
    base: dict,
    proposed: dict,
    *,
    delivery: bool,
) -> None:
    """
    Confirmation experiment:

        Existing conditions
            ->
        Existing conditions + ONE new condition

    The existing conditions must remain unchanged.

    The new condition may use an existing feature or introduce
    one additional supported feature.
    """

    base_conditions = base.get(
        "entry_conditions",
        [],
    )

    proposed_conditions = proposed.get(
        "entry_conditions",
        [],
    )

    if len(proposed_conditions) != len(base_conditions) + 1:
        raise Agent2GuardrailError(
            "A confirmation experiment must add exactly one "
            "entry condition."
        )

    base_signatures = _condition_signature_list(
        base_conditions
    )

    proposed_signatures = _condition_signature_list(
        proposed_conditions
    )

    remaining = proposed_signatures.copy()

    for signature in base_signatures:

        if signature not in remaining:
            raise Agent2GuardrailError(
                "A confirmation experiment changed an existing "
                "entry condition. Existing conditions must remain "
                "unchanged."
            )

        remaining.remove(signature)

    if len(remaining) != 1:
        raise Agent2GuardrailError(
            "A confirmation experiment must introduce exactly "
            "one new condition."
        )

    if delivery:
        new_condition = None

        for condition in proposed_conditions:

            signature = _condition_key(
                condition
            )

            if signature not in base_signatures:
                new_condition = condition
                break

        if new_condition is None:
            raise Agent2GuardrailError(
                "Could not identify the new delivery condition."
            )

        serialized = str(
            new_condition
        ).lower()

        if (
            "delivery_percentage" not in serialized
            and "average_delivery_percentage" not in serialized
        ):
            raise Agent2GuardrailError(
                "A delivery confirmation experiment must use "
                "delivery_percentage or "
                "average_delivery_percentage."
            )

    base_features = {
        _feature_key(feature)
        for feature in base.get(
            "features",
            [],
        )
    }

    proposed_features = {
        _feature_key(feature)
        for feature in proposed.get(
            "features",
            [],
        )
    }

    added_features = proposed_features - base_features

    if len(added_features) > 2:
        raise Agent2GuardrailError(
            "A confirmation experiment may introduce at most "
            "two new supported features."
        )


def _validate_robustness_experiment(
    base: dict,
    proposed: dict,
) -> None:
    """
    For the MVP, robustness experiments must preserve the research
    configuration.

    The existing Research Engine already provides stock-level,
    feature-level and market-regime diagnostics.

    Therefore Agent 2 should not invent arbitrary robustness
    dimensions yet.
    """

    if base != proposed:
        raise Agent2GuardrailError(
            "The MVP robustness experiment must use the same "
            "research configuration. Robustness analysis is "
            "provided by the deterministic Research Engine."
        )


def _validate_market_regime_experiment(
    base: dict,
    proposed: dict,
) -> None:
    """
    Market regime analysis is already produced by the deterministic
    Research Engine.

    Therefore no new entry condition is needed for this experiment
    type.
    """

    if base != proposed:
        raise Agent2GuardrailError(
            "Market-regime analysis must use the existing "
            "research configuration."
        )


def _validate_feature_interaction_experiment(
    base: dict,
    proposed: dict,
) -> None:
    """
    Controlled feature interaction.

    MVP rule:

    - preserve existing conditions
    - add exactly ONE condition
    - do not change existing conditions
    """

    base_conditions = base.get(
        "entry_conditions",
        [],
    )

    proposed_conditions = proposed.get(
        "entry_conditions",
        [],
    )

    if len(proposed_conditions) != len(base_conditions) + 1:
        raise Agent2GuardrailError(
            "A feature interaction experiment must add exactly "
            "one new condition."
        )

    base_signatures = _condition_signature_list(
        base_conditions
    )

    proposed_signatures = _condition_signature_list(
        proposed_conditions
    )

    remaining = proposed_signatures.copy()

    for signature in base_signatures:

        if signature not in remaining:
            raise Agent2GuardrailError(
                "A feature interaction experiment changed an "
                "existing condition."
            )

        remaining.remove(signature)

    if len(remaining) != 1:
        raise Agent2GuardrailError(
            "A feature interaction experiment must introduce "
            "exactly one new condition."
        )


# ======================================================================
# EXPERIMENT TYPE DISPATCH
# ======================================================================

def validate_controlled_change(
    request: Agent2Request,
    proposal: Agent2Proposal,
) -> None:
    """
    Validate the proposal according to its declared experiment type.
    """

    experiment_type = proposal.experiment_type

    if experiment_type not in ALLOWED_EXPERIMENT_TYPES:
        raise Agent2GuardrailError(
            f"Unsupported experiment type: {experiment_type}"
        )

    base = _request_dump(
        request.base_research_request
    )

    proposed = _request_dump(
        proposal.research_request
    )

    _validate_common_configuration(
        base,
        proposed,
        experiment_type=experiment_type,
    )

    if experiment_type == "threshold_sensitivity":
        _validate_threshold_experiment(
            base,
            proposed,
        )

    elif experiment_type == "horizon":
        _validate_horizon_experiment(
            base,
            proposed,
        )

    elif experiment_type == "confirmation_variable":
        _validate_confirmation_experiment(
            base,
            proposed,
            delivery=False,
        )

    elif experiment_type == "delivery_confirmation":
        _validate_confirmation_experiment(
            base,
            proposed,
            delivery=True,
        )

    elif experiment_type == "feature_interaction":
        _validate_feature_interaction_experiment(
            base,
            proposed,
        )

    elif experiment_type == "robustness":
        _validate_robustness_experiment(
            base,
            proposed,
        )

    elif experiment_type == "market_regime":
        _validate_market_regime_experiment(
            base,
            proposed,
        )


# ======================================================================
# PUBLIC VALIDATION FUNCTION
# ======================================================================

def validate_agent_2_proposal(
    request: Agent2Request,
    proposal: Agent2Proposal,
) -> Agent2Proposal:
    """
    Run every deterministic Agent 2 safety check.

    If any check fails, Agent2GuardrailError is raised.

    If all checks pass, the original validated proposal is returned.
    """

    if not isinstance(
        proposal,
        Agent2Proposal,
    ):
        raise Agent2GuardrailError(
            "Invalid Agent 2 proposal type."
        )

    # --------------------------------------------------------------
    # Re-validate the ResearchRequest independently.
    # --------------------------------------------------------------

    try:
        proposal.research_request = type(
            request.base_research_request
        ).model_validate(
            _request_dump(
                proposal.research_request
            )
        )
    except ValidationError as exc:

        raise Agent2GuardrailError(
            "Agent 2 produced an invalid ResearchRequest: "
            f"{exc}"
        ) from exc

    # --------------------------------------------------------------
    # Feature capability boundary.
    # --------------------------------------------------------------

    validate_features(
        proposal.research_request
    )

    # --------------------------------------------------------------
    # Final holdout governance.
    # --------------------------------------------------------------

    validate_holdout_governance(
        request,
        proposal,
    )

    # --------------------------------------------------------------
    # Duplicate protection.
    # --------------------------------------------------------------

    validate_not_duplicate(
        request,
        proposal,
    )

    # --------------------------------------------------------------
    # Lineage protection.
    # --------------------------------------------------------------

    validate_parent_lineage(
        request,
        proposal,
    )

    # --------------------------------------------------------------
    # Controlled-change protection.
    # --------------------------------------------------------------

    validate_controlled_change(
        request,
        proposal,
    )

    return proposal