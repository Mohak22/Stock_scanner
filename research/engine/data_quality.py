# -*- coding: utf-8 -*-
"""
Created on Mon Sep 14 22:33:34 2026

@author: mohak
"""

"""
Historical market-data quality audit.

This module is READ-ONLY.
It does not modify or delete the underlying dataset.
"""

"""Historical market-data quality audit.

This module is read-only.
It does not modify or delete the underlying dataset.
"""


import re

import pandas as pd


# ======================================================================
# COLUMN HELPERS
# ======================================================================

def _find_column(
    dataframe: pd.DataFrame,
    candidates: list[str],
) -> str | None:

    lookup = {
        str(column).strip().upper(): column
        for column in dataframe.columns
    }

    for candidate in candidates:
        key = candidate.strip().upper()

        if key in lookup:
            return lookup[key]

    return None


# ======================================================================
# DAILY RETURN
# ======================================================================

def _add_daily_return(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:

    result = dataframe.copy()

    symbol_column = _find_column(
        result,
        ["SYMBOL", "symbol"],
    )

    close_column = _find_column(
        result,
        ["CLOSE", "Close", "close"],
    )

    if symbol_column is None or close_column is None:
        raise ValueError(
            "Could not find SYMBOL and CLOSE columns."
        )

    result = result.sort_values(
        [symbol_column, "TIMESTAMP"]
    ).copy()

    result["_PREVIOUS_CLOSE"] = (
        result
        .groupby(symbol_column)[close_column]
        .shift(1)
    )

    result["_DAILY_RETURN_PCT"] = (
        (
            result[close_column]
            /
            result["_PREVIOUS_CLOSE"]
            - 1
        )
        * 100
    )

    return result


# ======================================================================
# MAIN AUDIT
# ======================================================================

def audit_historical_data(
    dataframe: pd.DataFrame,
    extreme_return_thresholds: tuple[float, ...] = (
        20.0,
        50.0,
        100.0,
        500.0,
    ),
) -> dict:

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError(
            "dataframe must be a pandas DataFrame."
        )

    if dataframe.empty:
        raise ValueError(
            "Historical dataframe is empty."
        )

    data = dataframe.copy()

    # ------------------------------------------------------------------
    # Required columns
    # ------------------------------------------------------------------

    symbol_column = _find_column(
        data,
        ["SYMBOL", "symbol"],
    )

    timestamp_column = _find_column(
        data,
        [
            "TIMESTAMP",
            "timestamp",
            "DATE",
            "Date",
            "date",
        ],
    )

    open_column = _find_column(
        data,
        ["OPEN", "Open", "open"],
    )

    high_column = _find_column(
        data,
        ["HIGH", "High", "high"],
    )

    low_column = _find_column(
        data,
        ["LOW", "Low", "low"],
    )

    close_column = _find_column(
        data,
        ["CLOSE", "Close", "close"],
    )

    volume_column = _find_column(
        data,
        ["VOLUME", "Volume", "volume"],
    )

    if symbol_column is None:
        raise ValueError("SYMBOL column not found.")

    if timestamp_column is None:
        raise ValueError("TIMESTAMP/DATE column not found.")

    if close_column is None:
        raise ValueError("CLOSE column not found.")

    # ------------------------------------------------------------------
    # Normalize
    # ------------------------------------------------------------------

    data["TIMESTAMP"] = pd.to_datetime(
        data[timestamp_column],
        errors="coerce",
    )

    data["_SYMBOL"] = (
        data[symbol_column]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    data["_CLOSE"] = pd.to_numeric(
        data[close_column],
        errors="coerce",
    )

    if open_column is not None:
        data["_OPEN"] = pd.to_numeric(
            data[open_column],
            errors="coerce",
        )

    if high_column is not None:
        data["_HIGH"] = pd.to_numeric(
            data[high_column],
            errors="coerce",
        )

    if low_column is not None:
        data["_LOW"] = pd.to_numeric(
            data[low_column],
            errors="coerce",
        )

    if volume_column is not None:
        data["_VOLUME"] = pd.to_numeric(
            data[volume_column],
            errors="coerce",
        )

    # ------------------------------------------------------------------
    # Basic counts
    # ------------------------------------------------------------------

    total_rows = len(data)

    total_stocks = int(
        data["_SYMBOL"].nunique()
    )

    invalid_timestamp = int(
        data["TIMESTAMP"].isna().sum()
    )

    invalid_close = int(
        data["_CLOSE"].isna().sum()
    )

    non_positive_close = int(
        (data["_CLOSE"] <= 0).sum()
    )

    # ------------------------------------------------------------------
    # Duplicate SYMBOL + DATE
    # ------------------------------------------------------------------

    duplicate_mask = data.duplicated(
        subset=[
            "_SYMBOL",
            "TIMESTAMP",
        ],
        keep=False,
    )

    duplicate_rows = int(
        duplicate_mask.sum()
    )

    duplicate_examples = (
        data.loc[
            duplicate_mask,
            [
                "_SYMBOL",
                "TIMESTAMP",
                "_CLOSE",
            ],
        ]
        .sort_values(
            [
                "_SYMBOL",
                "TIMESTAMP",
            ]
        )
        .head(50)
        .to_dict("records")
    )

    # ------------------------------------------------------------------
    # OHLC consistency
    # ------------------------------------------------------------------

    high_low_violations = 0
    close_outside_range = 0

    if (
        "_HIGH" in data.columns
        and "_LOW" in data.columns
    ):

        high_low_violations = int(
            (
                data["_HIGH"]
                <
                data["_LOW"]
            )
            .fillna(False)
            .sum()
        )

    if (
        "_HIGH" in data.columns
        and "_LOW" in data.columns
    ):

        close_outside_range = int(
            (
                (
                    data["_CLOSE"]
                    <
                    data["_LOW"]
                )
                |
                (
                    data["_CLOSE"]
                    >
                    data["_HIGH"]
                )
            )
            .fillna(False)
            .sum()
        )

    # ------------------------------------------------------------------
    # Daily returns
    # ------------------------------------------------------------------

    data = _add_daily_return(data)

    valid_daily_returns = data[
        data["_DAILY_RETURN_PCT"].notna()
    ].copy()

    # ------------------------------------------------------------------
    # Extreme daily movements
    # ------------------------------------------------------------------

    extreme_counts = {}

    for threshold in extreme_return_thresholds:

        count = int(
            (
                valid_daily_returns[
                    "_DAILY_RETURN_PCT"
                ].abs()
                >= threshold
            ).sum()
        )

        extreme_counts[
            f"abs_return_gte_{threshold:g}_pct"
        ] = count

    # ------------------------------------------------------------------
    # Largest daily movements
    # ------------------------------------------------------------------

    extreme_examples = (
        valid_daily_returns
        .assign(
            ABS_RETURN=lambda frame:
                frame[
                    "_DAILY_RETURN_PCT"
                ].abs()
        )
        .sort_values(
            "ABS_RETURN",
            ascending=False,
        )
        .head(100)
    )

    extreme_columns = [
        "_SYMBOL",
        "TIMESTAMP",
        "_PREVIOUS_CLOSE",
        "_CLOSE",
        "_DAILY_RETURN_PCT",
    ]

    extreme_columns = [
        column
        for column in extreme_columns
        if column in extreme_examples.columns
    ]

    extreme_examples = (
        extreme_examples[
            extreme_columns
        ]
        .to_dict("records")
    )

    # ------------------------------------------------------------------
    # Largest positive / negative movements
    # ------------------------------------------------------------------

    largest_positive = (
        valid_daily_returns
        .sort_values(
            "_DAILY_RETURN_PCT",
            ascending=False,
        )
        .head(50)[
            extreme_columns
        ]
        .to_dict("records")
    )

    largest_negative = (
        valid_daily_returns
        .sort_values(
            "_DAILY_RETURN_PCT",
            ascending=True,
        )
        .head(50)[
            extreme_columns
        ]
        .to_dict("records")
    )

    # ------------------------------------------------------------------
    # Long gaps between observations
    # ------------------------------------------------------------------

    gap_data = (
        data[
            [
                "_SYMBOL",
                "TIMESTAMP",
            ]
        ]
        .sort_values(
            [
                "_SYMBOL",
                "TIMESTAMP",
            ]
        )
        .copy()
    )

    gap_data["_PREVIOUS_DATE"] = (
        gap_data
        .groupby("_SYMBOL")["TIMESTAMP"]
        .shift(1)
    )

    gap_data["_GAP_DAYS"] = (
        gap_data["TIMESTAMP"]
        -
        gap_data["_PREVIOUS_DATE"]
    ).dt.days

    suspicious_gaps = (
        gap_data[
            gap_data["_GAP_DAYS"] > 10
        ]
        .sort_values(
            "_GAP_DAYS",
            ascending=False,
        )
        .head(100)
        .to_dict("records")
    )

    # ------------------------------------------------------------------
    # Volume sanity
    # ------------------------------------------------------------------

    negative_volume = None

    if "_VOLUME" in data.columns:

        negative_volume = int(
            (
                data["_VOLUME"] < 0
            ).sum()
        )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    return {
        "summary": {
            "total_rows": total_rows,
            "stocks": total_stocks,
            "first_date": (
                data["TIMESTAMP"].min()
                .strftime("%Y-%m-%d")
                if data["TIMESTAMP"].notna().any()
                else None
            ),
            "last_date": (
                data["TIMESTAMP"].max()
                .strftime("%Y-%m-%d")
                if data["TIMESTAMP"].notna().any()
                else None
            ),
        },

        "basic_integrity": {
            "invalid_timestamp": invalid_timestamp,
            "invalid_close": invalid_close,
            "non_positive_close": non_positive_close,
            "duplicate_symbol_date_rows": duplicate_rows,
            "high_less_than_low": high_low_violations,
            "close_outside_high_low": close_outside_range,
            "negative_volume": negative_volume,
        },

        "extreme_daily_returns": {
            "counts": extreme_counts,
            "largest_movements": extreme_examples,
            "largest_positive": largest_positive,
            "largest_negative": largest_negative,
        },

        "date_gaps": {
            "gaps_over_10_days": suspicious_gaps,
        },
    }