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

    # =====================================================
    # PRICE DIFFERENCE
    # =====================================================

    delta = close_prices.diff()

    # =====================================================
    # GAINS & LOSSES
    # =====================================================

    gains = delta.clip(
        lower=0
    )

    losses = -delta.clip(
        upper=0
    )

    # =====================================================
    # EXPONENTIAL MOVING AVERAGES
    # =====================================================

    average_gain = gains.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    average_loss = losses.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    # =====================================================
    # RELATIVE STRENGTH
    # =====================================================

    relative_strength = (
        average_gain / average_loss
    )

    # =====================================================
    # RSI
    # =====================================================

    rsi = 100 - (

        100 / (
            1 + relative_strength
        )
    )

    # =====================================================
    # LATEST RSI VALUE
    # =====================================================

    latest_rsi = round(
        rsi.iloc[-1],
        2
    )

    return latest_rsi