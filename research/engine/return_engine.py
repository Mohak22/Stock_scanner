# -*- coding: utf-8 -*-
"""
Created on Sun Aug 30 15:01:13 2026

@author: mohak
"""

"""
Generic Forward Return Engine

Purpose
-------
Calculate arbitrary future returns for historical stock data.

Example:

    T close
        |
        +---- T+1 return
        +---- T+3 return
        +---- T+5 return
        +---- T+10 return

This engine is designed for the Strategy Inventor.

It is intentionally independent from the existing
analysis/calculators/return_calculator.py because that
calculator is designed for recommendation analysis with
fixed BTST / 7D / 14D horizons.
"""

import pandas as pd


# ======================================================================
# FORWARD RETURNS
# ======================================================================

def calculate_forward_returns(
    dataframe: pd.DataFrame,
    horizons: list[int]
) -> pd.DataFrame:
    """
    Calculate future close-to-close returns.

    Parameters
    ----------
    dataframe:
        Historical stock dataframe.

        Required columns:

            SYMBOL
            TIMESTAMP
            CLOSE

        The dataframe should contain historical observations
        for one or multiple stocks.

    horizons:
        Number of future trading sessions.

        Example:

            [1, 3, 5, 10]

    Returns
    -------
    pd.DataFrame

        Original dataframe plus:

            RETURN_T1
            RETURN_T3
            RETURN_T5
            RETURN_T10

        Returns are expressed as percentages.

    Example
    -------
    If:

        CLOSE(T)   = 100
        CLOSE(T+3) = 108

    then:

        RETURN_T3 = 8.0
    """

    # ==================================================================
    # INPUT VALIDATION
    # ==================================================================

    if not isinstance(
        dataframe,
        pd.DataFrame
    ):

        raise TypeError(
            "dataframe must be a pandas DataFrame."
        )


    if not horizons:

        raise ValueError(
            "horizons must contain at least one value."
        )


    # ==================================================================
    # VALIDATE HORIZONS
    # ==================================================================

    cleaned_horizons = []

    for horizon in horizons:

        if not isinstance(
            horizon,
            int
        ):

            raise TypeError(
                "Every horizon must be an integer."
            )

        if horizon <= 0:

            raise ValueError(
                "Every horizon must be greater than zero."
            )

        cleaned_horizons.append(
            horizon
        )


    cleaned_horizons = sorted(
        set(cleaned_horizons)
    )


    # ==================================================================
    # COPY
    # ==================================================================

    result = dataframe.copy()


    # ==================================================================
    # COLUMN DETECTION
    # ==================================================================

    symbol_column = _find_column(
        result,
        [
            "SYMBOL",
            "symbol",
            "stock_symbol"
        ]
    )

    date_column = _find_column(
        result,
        [
            "TIMESTAMP",
            "timestamp",
            "Date",
            "date"
        ]
    )

    close_column = _find_column(
        result,
        [
            "CLOSE",
            "Close",
            "close"
        ]
    )


    # ==================================================================
    # NORMALISE DATE
    # ==================================================================

    result[date_column] = pd.to_datetime(
        result[date_column],
        errors="coerce"
    )


    # ==================================================================
    # NORMALISE CLOSE
    # ==================================================================

    result[close_column] = pd.to_numeric(
        result[close_column],
        errors="coerce"
    )


    # ==================================================================
    # REMOVE INVALID ROWS
    # ==================================================================

    result = result.dropna(
        subset=[
            symbol_column,
            date_column,
            close_column
        ]
    ).copy()


    # ==================================================================
    # SORT
    # ==================================================================

    result = result.sort_values(
        by=[
            symbol_column,
            date_column
        ]
    ).reset_index(
        drop=True
    )


    # ==================================================================
    # CALCULATE FORWARD RETURNS
    # ==================================================================

    grouped = result.groupby(
        symbol_column,
        sort=False
    )[close_column]


    for horizon in cleaned_horizons:

        future_close = grouped.shift(
            -horizon
        )

        column_name = (
            f"RETURN_T{horizon}"
        )

        result[column_name] = (

            (
                future_close
                -
                result[close_column]
            )

            /

            result[close_column]

        ) * 100


    # ==================================================================
    # ROUND RETURNS
    # ==================================================================

    return_columns = [

        f"RETURN_T{horizon}"

        for horizon in cleaned_horizons

    ]

    result[return_columns] = (
        result[return_columns]
        .round(4)
    )


    return result


# ======================================================================
# COLUMN HELPER
# ======================================================================

def _find_column(
    dataframe: pd.DataFrame,
    candidates: list[str]
) -> str:

    for candidate in candidates:

        if candidate in dataframe.columns:

            return candidate


    raise ValueError(
        "Could not find required column. "
        f"Expected one of: {candidates}"
    )