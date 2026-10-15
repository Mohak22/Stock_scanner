# -*- coding: utf-8 -*-
"""
Created on Wed Oct 14 23:20:38 2026

@author: mohak
"""


import pytest
import pandas as pd

from research.engine.cost_model import (
    DEFAULT_COST_MODEL,
    apply_transaction_costs,
)


def test_flat_price_trade_has_negative_net_return():
    data = pd.DataFrame({
        "ENTRY_PRICE": [100.0],
        "OUTCOME_PRICE_T1": [100.0],
        "RETURN_T1": [0.0],
        "OUTCOME_ELIGIBLE_T1": [True],
        "MARKET_RETURN_T1": [0.0],
    })

    result, summary = apply_transaction_costs(data, [1])

    assert result.loc[0, "NET_RETURN_T1"] < 0
    assert result.loc[0, "ESTIMATED_COST_PCT_T1"] > 0
    assert summary["by_horizon"]["T+1"]["observations"] == 1


def test_costs_reduce_positive_gross_return():
    data = pd.DataFrame({
        "ENTRY_PRICE": [100.0],
        "OUTCOME_PRICE_T1": [110.0],
        "RETURN_T1": [10.0],
        "OUTCOME_ELIGIBLE_T1": [True],
        "MARKET_RETURN_T1": [2.0],
    })

    result, summary = apply_transaction_costs(data, [1])

    gross = result.loc[0, "RETURN_T1"]
    net = result.loc[0, "NET_RETURN_T1"]

    assert net < gross
    assert net > 0
    assert result.loc[0, "NET_EXCESS_RETURN_T1"] == pytest.approx(
        net - 2.0
    )
    assert summary["by_horizon"]["T+1"][
        "average_net_return_pct"
    ] == pytest.approx(net)


def test_ineligible_outcome_is_excluded_from_net_summary():
    data = pd.DataFrame({
        "ENTRY_PRICE": [100.0, 100.0],
        "OUTCOME_PRICE_T1": [105.0, 110.0],
        "RETURN_T1": [5.0, 10.0],
        "OUTCOME_ELIGIBLE_T1": [True, False],
        "MARKET_RETURN_T1": [1.0, 2.0],
    })

    result, summary = apply_transaction_costs(data, [1])

    assert pd.notna(result.loc[0, "NET_RETURN_T1"])
    assert pd.isna(result.loc[1, "NET_RETURN_T1"])
    assert summary["by_horizon"]["T+1"]["observations"] == 1


def test_cost_assumptions_are_reported_explicitly():
    data = pd.DataFrame({
        "ENTRY_PRICE": [100.0],
        "OUTCOME_PRICE_T1": [101.0],
        "RETURN_T1": [1.0],
        "OUTCOME_ELIGIBLE_T1": [True],
    })

    _, summary = apply_transaction_costs(data, [1])

    assumptions = summary["assumptions"]

    assert assumptions["brokerage_rate"] == 0.0
    assert assumptions["stt_rate"] == 0.001
    assert assumptions["slippage_bps_per_side"] == 5.0
    assert "Per-scrip DP/depository charges" in summary["excluded_costs"]
