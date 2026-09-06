# -*- coding: utf-8 -*-
"""
Created on Sun Sep  6 13:01:54 2026

@author: mohak
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_market_index(
    file_path: str | Path,
    start_date: pd.Timestamp | str,
    end_date: pd.Timestamp | str,
) -> pd.DataFrame:
    """
    Load a market index parquet file and return normalized market data.

    Expected source columns:
        Date
        Close

    Returned columns:
        TIMESTAMP
        MARKET_CLOSE
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Market index file not found: {file_path}"
        )

    dataframe = pd.read_parquet(file_path)

    required_columns = {
        "Date",
        "Close",
    }

    missing_columns = required_columns - set(dataframe.columns)

    if missing_columns:
        raise ValueError(
            f"Market index file '{file_path}' is missing required "
            f"columns: {sorted(missing_columns)}"
        )

    dataframe = dataframe[
        ["Date", "Close"]
    ].copy()

    dataframe["TIMESTAMP"] = pd.to_datetime(
        dataframe["Date"],
        errors="coerce",
    )

    dataframe["MARKET_CLOSE"] = pd.to_numeric(
        dataframe["Close"],
        errors="coerce",
    )

    dataframe = dataframe.dropna(
        subset=[
            "TIMESTAMP",
            "MARKET_CLOSE",
        ]
    )

    start_date = pd.Timestamp(start_date)
    end_date = pd.Timestamp(end_date)

    dataframe = dataframe[
        (dataframe["TIMESTAMP"] >= start_date)
        & (dataframe["TIMESTAMP"] <= end_date)
    ].copy()

    dataframe = (
        dataframe[
            [
                "TIMESTAMP",
                "MARKET_CLOSE",
            ]
        ]
        .sort_values("TIMESTAMP")
        .drop_duplicates(
            subset=["TIMESTAMP"],
            keep="last",
        )
        .reset_index(drop=True)
    )

    return dataframe