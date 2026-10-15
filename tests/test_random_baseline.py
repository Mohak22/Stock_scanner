# -*- coding: utf-8 -*-
"""
Created on Thu Oct 15 22:06:44 2026

@author: mohak
"""


import pandas as pd
import pytest

from research.engine.random_baseline import build_random_baseline


def make_frame(symbols, dates, returns):
    return pd.DataFrame({
        "SYMBOL": symbols,
        "TIMESTAMP": pd.to_datetime(dates),
        "OUTCOME_ELIGIBLE_T1": [True] * len(symbols),
        "NET_EXCESS_RETURN_T1": returns,
    })


def test_random_baseline_preserves_observation_and_date_counts():
    candidates = make_frame(
        ["A", "B", "C", "A", "B", "C"],
        [
            "2025-01-02", "2025-01-02", "2025-01-02",
            "2025-01-03", "2025-01-03", "2025-01-03",
        ],
        [-2.0, 0.0, 2.0, -1.0, 1.0, 3.0],
    )

    observed = make_frame(
        ["C", "C"],
        ["2025-01-02", "2025-01-03"],
        [2.0, 3.0],
    )

    result = build_random_baseline(
        candidate_data=candidates,
        signal_data=observed,
        horizons=[1],
        permutations=99,
        random_seed=42,
    )

    horizon = result["by_horizon"]["T+1"]

    assert horizon["observations"] == 2
    assert horizon["dates_with_signals"] == 2
    assert horizon["observed_mean_net_excess_return_pct"] == 2.5
    assert horizon["permutations_completed"] == 99
    assert 0 < horizon["nominal_one_sided_p_value"] <= 1


def test_random_baseline_is_reproducible():
    candidates = make_frame(
        ["A", "B", "C", "A", "B", "C"],
        [
            "2025-01-02", "2025-01-02", "2025-01-02",
            "2025-01-03", "2025-01-03", "2025-01-03",
        ],
        [-2.0, 0.0, 2.0, -1.0, 1.0, 3.0],
    )

    observed = make_frame(
        ["C", "C"],
        ["2025-01-02", "2025-01-03"],
        [2.0, 3.0],
    )

    first = build_random_baseline(
        candidates, observed, [1], permutations=99, random_seed=42
    )
    second = build_random_baseline(
        candidates, observed, [1], permutations=99, random_seed=42
    )

    assert (
        first["by_horizon"]["T+1"]["nominal_one_sided_p_value"]
        == second["by_horizon"]["T+1"]["nominal_one_sided_p_value"]
    )
    assert (
        first["by_horizon"]["T+1"]["random_mean_net_excess_return_pct"]
        == second["by_horizon"]["T+1"]["random_mean_net_excess_return_pct"]
    )


def test_random_baseline_rejects_insufficient_candidate_pool():
    candidates = make_frame(
        ["A"],
        ["2025-01-02"],
        [1.0],
    )

    observed = make_frame(
        ["B", "C"],
        ["2025-01-02", "2025-01-02"],
        [2.0, 3.0],
    )

    with pytest.raises(ValueError, match="eligible candidates"):
        build_random_baseline(
            candidates, observed, [1], permutations=9
        )


def test_random_baseline_reports_no_signals():
    result = build_random_baseline(
        candidate_data=pd.DataFrame(),
        signal_data=pd.DataFrame(),
        horizons=[1, 3],
        permutations=9,
    )

    assert result["by_horizon"]["T+1"]["status"] == "NO_SIGNALS"
    assert result["by_horizon"]["T+3"]["status"] == "NO_SIGNALS"
