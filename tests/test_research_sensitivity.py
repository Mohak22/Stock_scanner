# -*- coding: utf-8 -*-
"""
Created on Wed Oct 14 23:32:03 2026

@author: mohak
"""


import pandas as pd

from research.engine.research_engine import (
    build_research_diagnostics,
)


def test_survivorship_sensitivity_excludes_top_ten_percent():
    data = pd.DataFrame({
        "SYMBOL": ["AAA", "AAA", "BBB", "CCC"],
        "TIMESTAMP": pd.to_datetime([
            "2025-01-02",
            "2025-01-03",
            "2025-01-02",
            "2025-01-02",
        ]),
        "RETURN_T1": [10.0, 12.0, 2.0, 0.0],
    })

    result = build_research_diagnostics(
        dataframe=data,
        signal_data=data,
        horizons=[1],
        features=[],
    )

    sensitivity = result["survivorship_sensitivity"]
    horizon = sensitivity["by_horizon"]["T+1"]

    assert horizon["symbols_with_valid_outcomes"] == 3
    assert horizon["excluded_top_symbols_count"] == 1
    assert horizon["excluded_top_symbols"] == ["AAA"]
    assert horizon["remaining_symbols_with_signals"] == 2
    assert horizon["remaining_average_return"] == 1.0

    assert "not an unbiased performance estimate" in (
        sensitivity["interpretation"]
    )
