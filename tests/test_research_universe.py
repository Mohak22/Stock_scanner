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
            "SERIES": ["EQ", "EQ", "EQ"],
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
            "SERIES": ["EQ", "EQ"],
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
            "SERIES": ["EQ", "EQ", "EQ"],
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
            "SERIES": ["EQ"],
            "CLOSE": [100.0],
        }
    )

    with pytest.raises(ValueError, match="TIMESTAMP"):
        apply_point_in_time_universe(data)


def test_point_in_time_fails_when_no_valid_rows_remain():
    data = pd.DataFrame(
        {
            "SYMBOL": [None],
            "SERIES": ["EQ"],
            "TIMESTAMP": ["not-a-date"],
            "CLOSE": [100.0],
        }
    )

    with pytest.raises(
        ValueError,
        match="No valid historical EQ-bhavcopy symbol/date records",
    ):
        apply_point_in_time_universe(data)


def test_research_universe_routes_point_in_time_mode():
    data = pd.DataFrame(
        {
            "SYMBOL": ["OLDCO"],
            "SERIES": ["EQ"],
            "TIMESTAMP": ["2020-01-02"],
            "CLOSE": [100.0],
        }
    )

    result = apply_research_universe(
        data,
        membership_basis="point_in_time",
    )

    assert result["SYMBOL"].tolist() == ["OLDCO"]


def test_point_in_time_excludes_non_equity_series():
    data = pd.DataFrame(
        {
            "SYMBOL": ["RELIANCE", "RELIANCE", "OLDCO"],
            "SERIES": ["EQ", "BE", "EQ"],
            "TIMESTAMP": [
                "2020-01-02",
                "2020-01-02",
                "2020-01-02",
            ],
            "CLOSE": [100.0, 101.0, 50.0],
        }
    )

    result = apply_point_in_time_universe(data)

    assert set(result["SYMBOL"]) == {"RELIANCE", "OLDCO"}
    assert result["SERIES"].eq("EQ").all()


def test_session_coverage_passes_when_all_sessions_exist():
    from api.research.universe import validate_bhavcopy_session_coverage

    validate_bhavcopy_session_coverage(
        observed_dates=["2020-01-02", "2020-01-03"],
        expected_dates=["2020-01-02", "2020-01-03"],
    )


def test_session_coverage_fails_when_a_session_is_missing():
    from api.research.universe import validate_bhavcopy_session_coverage

    with pytest.raises(ValueError, match="missing 1"):
        validate_bhavcopy_session_coverage(
            observed_dates=["2020-01-02"],
            expected_dates=["2020-01-02", "2020-01-03"],
        )


def test_nifty_50_filter_uses_current_constituent_snapshot(monkeypatch):
    from api.research import universe as universe_module

    constituents = pd.DataFrame({
        "SYMBOL": ["RELIANCE", "TCS", "INFY"],
        "COMPANY_NAME": ["Reliance", "TCS", "Infosys"],
    })

    monkeypatch.setattr(
        universe_module,
        "load_nifty_50_universe_dataframe",
        lambda: constituents,
    )

    data = pd.DataFrame({
        "SYMBOL": ["RELIANCE", "TCS", "INFY", "HDFCBANK"],
        "CLOSE": [100, 200, 300, 400],
    })

    result = universe_module.apply_nifty_50_universe(data)

    assert set(result["SYMBOL"]) == {
        "RELIANCE",
        "TCS",
        "INFY",
    }
    assert "HDFCBANK" not in set(result["SYMBOL"])
