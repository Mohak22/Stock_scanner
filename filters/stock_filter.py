# -*- coding: utf-8 -*-
"""
Created on Mon May 25 15:13:57 2026

@author: mohak
"""

from __future__ import annotations

import pandas as pd

# =========================================================
# FILTER WEAK STOCKS
# =========================================================

def filter_weak_stocks(
    stock_dataframe: pd.DataFrame
) -> pd.DataFrame:

    filtered_dataframe = (

        stock_dataframe[
            (stock_dataframe["rsi_14"] < 35)
            &
            (stock_dataframe["entry_close_price"] >
             stock_dataframe["ema_50"])
            &
            (stock_dataframe["rsi_9"] >
             stock_dataframe["rsi_14"])
        ]

        .sort_values(
            by="rsi_14"
        )

        .reset_index(
            drop=True
        )
    )

    return filtered_dataframe