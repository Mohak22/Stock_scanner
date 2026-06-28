# -*- coding: utf-8 -*-
"""
Created on Sun May 24 11:27:56 2026

@author: mohak
"""

from __future__ import annotations

import pandas as pd


# =========================================================
# CALCULATE LATEST RSI
# =========================================================

def calculate_rsi(
    close_prices: pd.Series,
    period: int
) -> float | None:

    rsi_series = calculate_rsi_series(
        close_prices=close_prices,
        period=period
    )

    if rsi_series.empty:

        return None

    latest_rsi = (
        rsi_series
        .dropna()
    )

    if latest_rsi.empty:

        return None

    return round(
        float(
            latest_rsi.iloc[-1]
        ),
        2
    )


# =========================================================
# CALCULATE RSI SERIES
# =========================================================

def calculate_rsi_series(
    close_prices: pd.Series,
    period: int
) -> pd.Series:

    # =====================================================
    # INPUT VALIDATION
    # =====================================================

    if not isinstance(
        close_prices,
        pd.Series
    ):

        raise TypeError(
            "close_prices must be a pandas Series."
        )

    if period <= 0:

        raise ValueError(
            "period must be greater than zero."
        )

    if close_prices.empty:

        return pd.Series(
            dtype=float
        )

    # =====================================================
    # CLEAN INPUT
    # =====================================================

    close_prices = (
        close_prices
        .dropna()
        .astype(float)
    )

    if close_prices.empty:

        return pd.Series(
            dtype=float
        )

    # =====================================================
    # PRICE CHANGES
    # =====================================================

    delta = (
        close_prices
        .diff()
    )

    gain = (
        delta
        .clip(lower=0)
    )

    loss = (
        -delta
        .clip(upper=0)
    )

    # =====================================================
    # WILDER'S SMOOTHING
    # =====================================================

    average_gain = gain.ewm(
        com=period - 1,
        min_periods=period,
        adjust=False
    ).mean()

    average_loss = loss.ewm(
        com=period - 1,
        min_periods=period,
        adjust=False
    ).mean()

    # =====================================================
    # RELATIVE STRENGTH
    # =====================================================

    relative_strength = (
        average_gain
        /
        average_loss
    )

    # =====================================================
    # RSI
    # =====================================================

    rsi_series = (
        100
        -
        (
            100
            /
            (
                1 + relative_strength
            )
        )
    )

    return rsi_series