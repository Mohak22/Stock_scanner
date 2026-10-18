from __future__ import annotations

# -*- coding: utf-8 -*-
"""
Created on Sun Oct 18 13:43:22 2026

@author: mohak
"""


"""Multiple-testing corrections for research p-values."""


from copy import deepcopy
import math
from collections.abc import Mapping


def adjust_p_values(
    p_values: Mapping[str, float],
    alpha: float = 0.05,
) -> dict:
    """
    Calculate Bonferroni and Benjamini-Hochberg adjusted p-values.

    p_values maps hypothesis identifiers to raw p-values.
    The family must be defined by the caller before correction.
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be strictly between 0 and 1.")

    normalized = {}

    for hypothesis, value in p_values.items():
        p_value = float(value)

        if not math.isfinite(p_value) or not 0.0 <= p_value <= 1.0:
            raise ValueError(
                f"Invalid p-value for {hypothesis!r}: {value!r}"
            )

        normalized[str(hypothesis)] = p_value

    m = len(normalized)

    result = {
        "method": "bonferroni_and_benjamini_hochberg",
        "alpha": float(alpha),
        "hypothesis_count": m,
        "by_hypothesis": {},
    }

    if m == 0:
        return result

    # Deterministic sorting also handles tied p-values.
    ranked = sorted(
        normalized.items(),
        key=lambda item: (item[1], item[0]),
    )

    # Bonferroni-adjusted p-values.
    bonferroni = {
        hypothesis: min(1.0, p_value * m)
        for hypothesis, p_value in normalized.items()
    }

    # Raw BH values: p_(i) * m / i, with ranks starting at 1.
    bh_raw = [
        min(1.0, p_value * m / rank)
        for rank, (_, p_value) in enumerate(ranked, start=1)
    ]

    # Enforce monotonicity by taking cumulative minima backwards.
    bh_adjusted = [0.0] * m
    running_minimum = 1.0

    for index in range(m - 1, -1, -1):
        running_minimum = min(
            running_minimum,
            bh_raw[index],
        )
        bh_adjusted[index] = running_minimum

    bh_by_hypothesis = {
        hypothesis: bh_adjusted[index]
        for index, (hypothesis, _) in enumerate(ranked)
    }

    for hypothesis, raw_p_value in normalized.items():
        bonferroni_p = bonferroni[hypothesis]
        bh_p = bh_by_hypothesis[hypothesis]

        result["by_hypothesis"][hypothesis] = {
            "raw_p_value": raw_p_value,
            "bonferroni_adjusted_p_value": bonferroni_p,
            "bh_adjusted_p_value": bh_p,
            "significant_after_bonferroni": (
                bonferroni_p <= alpha
            ),
            "significant_after_bh": bh_p <= alpha,
        }

    return result


def apply_corrections_to_random_baseline(
    random_baseline: dict,
    alpha: float = 0.05,
) -> dict:
    """
    Apply corrections across valid horizon p-values in one stage.

    This family covers evaluation horizons within one research
    run and one stage. It does not account for separate runs,
    strategy variants, or experiments tried over time.
    """
    result = deepcopy(random_baseline)
    by_horizon = result.get("by_horizon", {})

    p_values = {}

    for horizon, metrics in by_horizon.items():
        if "nominal_one_sided_p_value" not in metrics:
            continue

        p_values[horizon] = metrics[
            "nominal_one_sided_p_value"
        ]

    correction = adjust_p_values(
        p_values=p_values,
        alpha=alpha,
    )

    correction["family_scope"] = (
        "Valid horizon p-values within one research run and "
        "one evaluation stage."
    )
    correction["limitations"] = [
        "Does not correct for separate research runs or "
        "strategy variants tried over time.",
        "Does not repair invalid p-values or correct for "
        "temporal dependence and overlapping outcomes.",
        "Statistical significance does not establish "
        "future profitability.",
    ]

    result["multiple_testing"] = correction

    for horizon, metrics in by_horizon.items():
        hypothesis_result = correction["by_hypothesis"].get(
            horizon
        )

        if hypothesis_result is None:
            metrics["bonferroni_adjusted_p_value"] = None
            metrics["bh_adjusted_p_value"] = None
            metrics["significant_after_bonferroni"] = None
            metrics["significant_after_bh"] = None
            metrics["multiple_testing_family_size"] = 0
            continue

        metrics.update(hypothesis_result)
        metrics["multiple_testing_family_size"] = (
            correction["hypothesis_count"]
        )

    return result
