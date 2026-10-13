# -*- coding: utf-8 -*-
"""
Created on Tue Oct 13 16:49:33 2026

@author: mohak
"""

import pandas as pd
import pytest

from api.research.universe import (
    apply_point_in_time_universe,
    apply_research_universe,
)


def test_point_in_time_keeps_historical_symbols_without_current_snapshot():
    # OLDCO represents a company that may no longer appear in today's
    # universe. The historical bhavcopy record must still be retained.
    data = pd.DataFrame(
        {
            "SYMBOL": ["OLDCO", "RELIANCE", "NEWCO"],
            "TIMESTAMP": [
                "2020-01-02",
                "2020-01-02",
                "2025-01-02",
            ],
            "CLOSE": [100.0, 2000.0, 50.0],
        }
    )

    result = apply_point_in_time_universe(data)

    assert set(result["SYMBOL"]) == {
        "OLDCO",
        "RELIANCE",
        "NEWCO",
    }

    assert "CLOSE" in result.columns


def test_point_in_time_normalizes_symbol_and_date():
    data = pd.DataFrame(
        {
            "SYMBOL": [" reliance ", "tcs"],
            "TIMESTAMP": [
                "2020-01-02 15:30:00",
                "2020-01-03 00:00:00",
            ],
            "CLOSE": [100.0, 200.0],
        }
    )

    result = apply_point_in_time_universe(data)

    assert result["SYMBOL"].tolist() == ["RELIANCE", "TCS"]
    assert result["TIMESTAMP"].tolist() == [
        pd.Timestamp("2020-01-02"),
        pd.Timestamp("2020-01-03"),
    ]


def test_point_in_time_drops_invalid_symbol_or_timestamp():
    data = pd.DataFrame(
        {
            "SYMBOL": ["RELIANCE", None, "TCS"],
            "TIMESTAMP": [
                "2020-01-02",
                "2020-01-02",
                "not-a-date",
            ],
            "CLOSE": [100.0, 200.0, 300.0],
        }
    )

    result = apply_point_in_time_universe(data)

    assert len(result) == 1
    assert result.iloc[0]["SYMBOL"] == "RELIANCE"


def test_point_in_time_fails_when_required_columns_are_missing():
    data = pd.DataFrame(
        {
            "SYMBOL": ["RELIANCE"],
            "CLOSE": [100.0],
        }
    )

    with pytest.raises(ValueError, match="TIMESTAMP"):
        apply_point_in_time_universe(data)


def test_point_in_time_fails_when_no_valid_rows_remain():
    data = pd.DataFrame(
        {
            "SYMBOL": [None],
            "TIMESTAMP": ["not-a-date"],
            "CLOSE": [100.0],
        }
    )

    with pytest.raises(ValueError, match="No valid symbol/date records"):
        apply_point_in_time_universe(data)


def test_research_universe_routes_point_in_time_mode():
    data = pd.DataFrame(
        {
            "SYMBOL": ["OLDCO"],
            "TIMESTAMP": ["2020-01-02"],
            "CLOSE": [100.0],
        }
    )

    result = apply_research_universe(
        data,
        membership_basis="point_in_time",
    )

    assert result["SYMBOL"].tolist() == ["OLDCO"]
