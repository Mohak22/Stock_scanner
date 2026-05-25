# -*- coding: utf-8 -*-
"""
Created on Sun May 24 16:10:19 2026

@author: mohak
"""

from __future__ import annotations

import pandas as pd

# =========================================================
# ANALYZE MARKET CONDITION
# =========================================================

def analyze_market_condition(
    market_dataframe: pd.DataFrame
) -> str:

    rsi14_values = (
        market_dataframe["RSI_14"]
        .tolist()
    )
    
    # =====================================================
    # MARKET REGIME LOGIC
    # =====================================================

    if all(
        rsi < 35
        for rsi in rsi14_values
    ):

        market_status = "PANIC"

    elif all(
        rsi > 45
        for rsi in rsi14_values
    ):

        market_status = "HEALTHY"

    else:

        market_status = "NEUTRAL"

    return market_status