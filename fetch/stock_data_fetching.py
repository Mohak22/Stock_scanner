# -*- coding: utf-8 -*-
"""
Created on Wed May 20 22:09:34 2026

@author: mohak
"""

from __future__ import annotations

from typing import Dict

import pandas as pd
import yfinance as yf

# =========================================================
# FETCH STOCK DATA
# =========================================================

def fetch_stock_data(
    weak_sector_dataframe: pd.DataFrame,
    master_dataframe: pd.DataFrame
) -> Dict[str, pd.DataFrame]:

    stock_data = {}

    # =====================================================
    # EXTRACT WEAK SECTORS
    # =====================================================

    weak_sectors = (
        weak_sector_dataframe["Sector"]
        .tolist()
    )

    # =====================================================
    # FILTER STOCKS
    # =====================================================

    filtered_dataframe = (

        master_dataframe[

            master_dataframe["sector"]
            .isin(weak_sectors)
        ]
    )

    # =====================================================
    # UNIQUE STOCKS
    # =====================================================

    symbols = (

        filtered_dataframe["Symbol"]
        .dropna()
        .unique()
        .tolist()
    )

    # =====================================================
    # FETCH STOCKS
    # =====================================================

    for symbol in symbols:

        ticker = (
            f"{symbol}.NS"
        )

        try:

            print(
                f"Fetching {ticker}"
            )

            ticker_object = yf.Ticker(
                ticker
            )

            data = ticker_object.history(
                period="3mo",
                auto_adjust=True
            )

            if data.empty:

                continue

            data = data.dropna()

            if data.empty:

                continue

            stock_data[symbol] = (
                data
            )

        except Exception as error:

            print(
                f"Error fetching "
                f"{ticker}"
            )

            print(error)

    return stock_data