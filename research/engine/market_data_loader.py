# -*- coding: utf-8 -*-
"""
Created on Sun Sep  6 13:01:54 2026

@author: mohak
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def load_market_index(
    source: str | Path | pd.DataFrame,
    start_date: pd.Timestamp | str,
    end_date: pd.Timestamp | str,
) -> pd.DataFrame:
    """
    Load and normalize market index data.

    source can be either:

        - a local parquet path
        - a pandas DataFrame

    The Research API should normally provide a DataFrame
    downloaded from GitHub.
    """

    # --------------------------------------------------------------
    # LOAD SOURCE
    # --------------------------------------------------------------

    if isinstance(
        source,
        pd.DataFrame,
    ):

        dataframe = source.copy()

    else:

        file_path = Path(source)

        if not file_path.exists():

            raise FileNotFoundError(
                f"Market index file not found: {file_path}"
            )

        dataframe = pd.read_parquet(
            file_path
        )

    # --------------------------------------------------------------
    # VALIDATE
    # --------------------------------------------------------------

    required_columns = {
        "Date",
        "Close",
    }

    missing_columns = (
        required_columns
        - set(dataframe.columns)
    )

    if missing_columns:

        raise ValueError(
            "Market index data is missing "
            f"required columns: {sorted(missing_columns)}"
        )

    # --------------------------------------------------------------
    # SELECT REQUIRED DATA
    # --------------------------------------------------------------

    dataframe = dataframe[
        [
            "Date",
            "Close",
        ]
    ].copy()

    # --------------------------------------------------------------
    # NORMALIZE
    # --------------------------------------------------------------

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

    # --------------------------------------------------------------
    # DATE RANGE
    # --------------------------------------------------------------

    start_date = pd.Timestamp(
        start_date
    )

    end_date = pd.Timestamp(
        end_date
    )

    dataframe = dataframe[
        (
            dataframe["TIMESTAMP"]
            >= start_date
        )
        &
        (
            dataframe["TIMESTAMP"]
            <= end_date
        )
    ].copy()

    # --------------------------------------------------------------
    # FINAL FORMAT
    # --------------------------------------------------------------

    dataframe = (
        dataframe[
            [
                "TIMESTAMP",
                "MARKET_CLOSE",
            ]
        ]
        .sort_values(
            "TIMESTAMP"
        )
        .drop_duplicates(
            subset=["TIMESTAMP"],
            keep="last",
        )
        .reset_index(
            drop=True
        )
    )

    return dataframe