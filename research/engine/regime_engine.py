# -*- coding: utf-8 -*-
"""
Created on Sun Sep  6 14:11:11 2026

@author: mohak
"""

"""
Causal market regime engine.

The regime at date T is calculated exclusively from market
information available at or before T.

Default:

    20-trading-day trailing NIFTY 50 return

        < -5%       -> BEAR
        -5% to +5%  -> NEUTRAL
        > +5%       -> BULL
"""

import pandas as pd


DEFAULT_LOOKBACK = 20
DEFAULT_BEAR_THRESHOLD = -5.0
DEFAULT_BULL_THRESHOLD = 5.0


# ======================================================================
# COLUMN RESOLUTION
# ======================================================================

def _resolve_timestamp_column(
    dataframe: pd.DataFrame,
) -> str:
    """
    Find the market date column.
    """

    candidates = [
        "TIMESTAMP",
        "Date",
        "date",
        "DATE",
        "Datetime",
        "datetime",
        "DATETIME",
        "Timestamp",
        "timestamp",
    ]

    for column in candidates:

        if column in dataframe.columns:
            return column

    normalized = {
        str(column).strip().upper(): column
        for column in dataframe.columns
    }

    for candidate in candidates:

        key = candidate.upper()

        if key in normalized:
            return normalized[key]

    raise ValueError(
        "Market dataframe must contain a date/timestamp "
        f"column. Available columns: "
        f"{list(dataframe.columns)}"
    )


def _resolve_price_column(
    dataframe: pd.DataFrame,
) -> str:
    """
    Find the market price column.

    Supports common schemas including:

        CLOSE
        Close
        close
        Adj Close
        ADJ_CLOSE
        close_price
        PX_LAST
        LAST

    Also handles MultiIndex columns.
    """

    candidates = [
        "CLOSE",
        "Close",
        "close",
        "Adj Close",
        "ADJ_CLOSE",
        "adj_close",
        "CLOSE_PRICE",
        "Close Price",
        "close_price",
        "ADJ_CLOSE_PRICE",
        "Adj Close Price",
        "PX_LAST",
        "LAST",
    ]

    # ----------------------------------------------------------
    # Exact
    # ----------------------------------------------------------

    for column in candidates:

        if column in dataframe.columns:
            return column

    # ----------------------------------------------------------
    # Case insensitive
    # ----------------------------------------------------------

    normalized = {
        str(column).strip().upper(): column
        for column in dataframe.columns
    }

    for candidate in candidates:

        key = candidate.strip().upper()

        if key in normalized:
            return normalized[key]

    # ----------------------------------------------------------
    # MultiIndex
    # ----------------------------------------------------------

    if isinstance(
        dataframe.columns,
        pd.MultiIndex,
    ):

        for column in dataframe.columns:

            parts = [
                str(part).strip().upper()
                for part in column
            ]

            if "CLOSE" in parts:

                return column

    # ----------------------------------------------------------
    # Structural fallback
    # ----------------------------------------------------------

    for column in dataframe.columns:

        text = str(column).strip().upper()

        if "CLOSE" in text:
            return column

        if text in {
            "PX_LAST",
            "LAST",
        }:
            return column

    raise ValueError(
        "Unable to identify the market price column. "
        f"Available columns: "
        f"{list(dataframe.columns)}"
    )


# ======================================================================
# NORMALIZATION
# ======================================================================

def _normalize_market_dataframe(
    market_dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normalize market data into:

        TIMESTAMP
        CLOSE
    """

    if market_dataframe is None:

        raise ValueError(
            "Market dataframe cannot be None."
        )

    if market_dataframe.empty:

        raise ValueError(
            "Market dataframe is empty."
        )

    dataframe = market_dataframe.copy()

    # ----------------------------------------------------------
    # Timestamp
    # ----------------------------------------------------------

    timestamp_column = (
        _resolve_timestamp_column(
            dataframe
        )
    )

    if timestamp_column != "TIMESTAMP":

        dataframe = dataframe.rename(
            columns={
                timestamp_column: "TIMESTAMP"
            }
        )

    # ----------------------------------------------------------
    # Price
    # ----------------------------------------------------------

    price_column = (
        _resolve_price_column(
            dataframe
        )
    )

    if price_column != "CLOSE":

        dataframe = dataframe.rename(
            columns={
                price_column: "CLOSE"
            }
        )

    # ----------------------------------------------------------
    # Values
    # ----------------------------------------------------------

    dataframe["TIMESTAMP"] = pd.to_datetime(
        dataframe["TIMESTAMP"],
        errors="coerce",
    )

    dataframe["CLOSE"] = pd.to_numeric(
        dataframe["CLOSE"],
        errors="coerce",
    )

    dataframe = (
        dataframe
        .dropna(
            subset=[
                "TIMESTAMP",
                "CLOSE",
            ]
        )
        .sort_values("TIMESTAMP")
        .drop_duplicates(
            subset=["TIMESTAMP"],
            keep="last",
        )
        .reset_index(drop=True)
    )

    if dataframe.empty:

        raise ValueError(
            "Market dataframe contains no valid "
            "timestamp/price observations."
        )

    return dataframe


# ======================================================================
# REGIME CALCULATION
# ======================================================================

def calculate_market_regime(
    market_dataframe: pd.DataFrame,
    lookback: int = DEFAULT_LOOKBACK,
    bear_threshold: float = DEFAULT_BEAR_THRESHOLD,
    bull_threshold: float = DEFAULT_BULL_THRESHOLD,
) -> pd.DataFrame:
    """
    Calculate causal market regime.

    No future information is used.
    """

    if lookback <= 0:

        raise ValueError(
            "Market regime lookback must be positive."
        )

    if bear_threshold >= bull_threshold:

        raise ValueError(
            "bear_threshold must be smaller than "
            "bull_threshold."
        )

    dataframe = _normalize_market_dataframe(
        market_dataframe
    )

    # ----------------------------------------------------------
    # T vs T-lookback trading observation
    # ----------------------------------------------------------

    dataframe["MARKET_TRAILING_RETURN"] = (
        (
            dataframe["CLOSE"]
            / dataframe["CLOSE"].shift(lookback)
        )
        - 1
    ) * 100

    # ----------------------------------------------------------
    # Regime
    # ----------------------------------------------------------

    dataframe["MARKET_REGIME"] = pd.Series(
        pd.NA,
        index=dataframe.index,
        dtype="object",
    )

    valid = (
        dataframe["MARKET_TRAILING_RETURN"]
        .notna()
    )

    dataframe.loc[
        valid
        & (
            dataframe["MARKET_TRAILING_RETURN"]
            < bear_threshold
        ),
        "MARKET_REGIME",
    ] = "BEAR"

    dataframe.loc[
        valid
        & (
            dataframe["MARKET_TRAILING_RETURN"]
            >= bear_threshold
        )
        & (
            dataframe["MARKET_TRAILING_RETURN"]
            <= bull_threshold
        ),
        "MARKET_REGIME",
    ] = "NEUTRAL"

    dataframe.loc[
        valid
        & (
            dataframe["MARKET_TRAILING_RETURN"]
            > bull_threshold
        ),
        "MARKET_REGIME",
    ] = "BULL"

    return dataframe[
        [
            "TIMESTAMP",
            "CLOSE",
            "MARKET_TRAILING_RETURN",
            "MARKET_REGIME",
        ]
    ].copy()


# ======================================================================
# ATTACH REGIME TO SIGNALS
# ======================================================================

def attach_market_regime(
    signal_data: pd.DataFrame,
    market_dataframe: pd.DataFrame,
    lookback: int = DEFAULT_LOOKBACK,
    bear_threshold: float = DEFAULT_BEAR_THRESHOLD,
    bull_threshold: float = DEFAULT_BULL_THRESHOLD,
) -> pd.DataFrame:
    """
    Attach causal market regime to signal rows.
    """

    result = signal_data.copy()

    if result.empty:

        result["MARKET_TRAILING_RETURN"] = (
            pd.Series(
                dtype="float64"
            )
        )

        result["MARKET_REGIME"] = (
            pd.Series(
                dtype="object"
            )
        )

        return result

    if "TIMESTAMP" not in result.columns:

        raise ValueError(
            "Signal dataframe must contain TIMESTAMP."
        )

    result["TIMESTAMP"] = pd.to_datetime(
        result["TIMESTAMP"],
        errors="coerce",
    )

    result = result.dropna(
        subset=["TIMESTAMP"]
    ).copy()

    regime_data = calculate_market_regime(
        market_dataframe=market_dataframe,
        lookback=lookback,
        bear_threshold=bear_threshold,
        bull_threshold=bull_threshold,
    )

    regime_data = regime_data[
        [
            "TIMESTAMP",
            "MARKET_TRAILING_RETURN",
            "MARKET_REGIME",
        ]
    ]

    result = result.drop(
        columns=[
            "MARKET_TRAILING_RETURN",
            "MARKET_REGIME",
        ],
        errors="ignore",
    )

    result = result.merge(
        regime_data,
        on="TIMESTAMP",
        how="left",
    )

    return result