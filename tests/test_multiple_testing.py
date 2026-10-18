# -*- coding: utf-8 -*-
"""
Created on Sun Oct 18 13:45:49 2026

@author: mohak
"""


import pytest

from research.engine.multiple_testing import (
    adjust_p_values,
    apply_corrections_to_random_baseline,
)


def test_known_bonferroni_and_bh_values():
    p_values = {
        "A": 0.001,
        "B": 0.010,
        "C": 0.030,
        "D": 0.040,
        "E": 0.200,
    }

    result = adjust_p_values(p_values, alpha=0.05)
    values = result["by_hypothesis"]

    assert result["hypothesis_count"] == 5

    assert values["A"]["bonferroni_adjusted_p_value"] == pytest.approx(0.005)
    assert values["B"]["bonferroni_adjusted_p_value"] == pytest.approx(0.050)
    assert values["C"]["bonferroni_adjusted_p_value"] == pytest.approx(0.150)
    assert values["E"]["bonferroni_adjusted_p_value"] == pytest.approx(1.000)

    assert values["A"]["bh_adjusted_p_value"] == pytest.approx(0.005)
    assert values["B"]["bh_adjusted_p_value"] == pytest.approx(0.025)
    assert values["C"]["bh_adjusted_p_value"] == pytest.approx(0.050)
    assert values["D"]["bh_adjusted_p_value"] == pytest.approx(0.050)
    assert values["E"]["bh_adjusted_p_value"] == pytest.approx(0.200)

    assert values["A"]["significant_after_bh"] is True
    assert values["D"]["significant_after_bh"] is True
    assert values["E"]["significant_after_bh"] is False


def test_bh_adjustment_handles_tied_p_values():
    result = adjust_p_values({
        "A": 0.01,
        "B": 0.01,
        "C": 0.20,
    })

    values = result["by_hypothesis"]

    assert values["A"]["bh_adjusted_p_value"] == pytest.approx(0.015)
    assert values["B"]["bh_adjusted_p_value"] == pytest.approx(0.015)
    assert values["C"]["bh_adjusted_p_value"] == pytest.approx(0.20)


def test_empty_family_is_supported():
    result = adjust_p_values({})

    assert result["hypothesis_count"] == 0
    assert result["by_hypothesis"] == {}


@pytest.mark.parametrize("invalid_p", [-0.01, 1.01, float("nan"), float("inf")])
def test_invalid_p_values_are_rejected(invalid_p):
    with pytest.raises(ValueError, match="Invalid p-value"):
        adjust_p_values({"A": invalid_p})


def test_invalid_alpha_is_rejected():
    with pytest.raises(ValueError, match="alpha"):
        adjust_p_values({"A": 0.01}, alpha=1.0)


def test_random_baseline_gets_adjusted_values_without_losing_raw_p():
    baseline = {
        "by_horizon": {
            "T+1": {
                "nominal_one_sided_p_value": 0.01,
                "observations": 100,
            },
            "T+3": {
                "nominal_one_sided_p_value": 0.04,
                "observations": 100,
            },
            "T+5": {
                "status": "NO_VALID_OUTCOMES",
                "observations": 0,
            },
        }
    }

    result = apply_corrections_to_random_baseline(baseline)

    assert (
        result["by_horizon"]["T+1"]["nominal_one_sided_p_value"]
        == 0.01
    )
    assert (
        result["by_horizon"]["T+1"]["bonferroni_adjusted_p_value"]
        == pytest.approx(0.02)
    )
    assert (
        result["by_horizon"]["T+1"]["bh_adjusted_p_value"]
        == pytest.approx(0.02)
    )
    assert result["multiple_testing"]["hypothesis_count"] == 2
    assert result["by_horizon"]["T+5"]["bh_adjusted_p_value"] is None

    # The original input must remain unchanged.
    assert "multiple_testing" not in baseline
