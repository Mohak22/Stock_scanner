# -*- coding: utf-8 -*-
"""
Created on Sun Sep  6 13:01:04 2026

@author: mohak
"""

from __future__ import annotations

import pandas as pd


def calculate_market_forward_returns(
    market_dataframe: pd.DataFrame,
    horizons: list[int],
) -> pd.DataFrame:
    """
    Calculate forward market returns for arbitrary horizons.

    Required columns:
        TIMESTAMP
        MARKET_CLOSE

    Creates:
        MARKET_RETURN_T1
        MARKET_RETURN_T3
        MARKET_RETURN_T5
        etc.

    Returns are expressed as percentages.
    """

    required_columns = {
        "TIMESTAMP",
        "MARKET_CLOSE",
    }

    missing_columns = required_columns - set(market_dataframe.columns)

    if missing_columns:
        raise ValueError(
            "Market return calculation requires columns: "
            f"{sorted(required_columns)}. "
            f"Missing: {sorted(missing_columns)}"
        )

    result = market_dataframe.copy()

    result["TIMESTAMP"] = pd.to_datetime(
        result["TIMESTAMP"],
        errors="coerce",
    )

    result["MARKET_CLOSE"] = pd.to_numeric(
        result["MARKET_CLOSE"],
        errors="coerce",
    )

    result = result.dropna(
        subset=[
            "TIMESTAMP",
            "MARKET_CLOSE",
        ]
    )

    result = (
        result
        .sort_values("TIMESTAMP")
        .drop_duplicates(
            subset=["TIMESTAMP"],
            keep="last",
        )
        .reset_index(drop=True)
    )

    for horizon in horizons:
        horizon = int(horizon)

        if horizon <= 0:
            raise ValueError(
                f"Forward return horizon must be positive. "
                f"Received: {horizon}"
            )

        future_close = result["MARKET_CLOSE"].shift(-horizon)

        result[f"MARKET_RETURN_T{horizon}"] = (
            (future_close / result["MARKET_CLOSE"]) - 1
        ) * 100

    return result