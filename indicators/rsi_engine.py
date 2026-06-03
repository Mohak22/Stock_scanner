# -*- coding: utf-8 -*-
"""
Created on Sun May 24 11:27:56 2026

@author: mohak
"""

from __future__ import annotations

import pandas as pd

# =========================================================
# CALCULATE RSI
# =========================================================

def calculate_rsi(
    close_prices: pd.Series,
    period: int
) -> float:

    rsi_series = calculate_rsi_series(
        close_prices,
        period
    )

    latest_rsi = round(
        rsi_series.iloc[-1],
        2
    )

    return latest_rsi

def calculate_rsi_series(
    close_prices: pd.Series,
    period: int
) -> pd.Series:

    delta = close_prices.diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)

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

    relative_strength = (
        average_gain
        /
        average_loss
    )

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