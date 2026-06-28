# -*- coding: utf-8 -*-
"""
Created on Wed May 20 22:09:34 2026

@author: mohak
"""

from __future__ import annotations

from typing import Dict, List

import pandas as pd
import yfinance as yf

# =========================================================
# FETCH STOCK DATA
# =========================================================

def fetch_stock_data(
    symbols: List[str],
    period: str = "3mo",
    auto_adjust: bool = False,
    exchange_suffix: str = ".NS"
) -> Dict[str, pd.DataFrame]:

    stock_data: Dict[
        str,
        pd.DataFrame
    ] = {}

    # =====================================================
    # REMOVE DUPLICATES
    # =====================================================

    symbols = list(
        set(symbols)
    )

    # =====================================================
    # FETCH EACH STOCK
    # =====================================================

    for symbol in symbols:

        ticker = (
            f"{symbol}"
            f"{exchange_suffix}"
        )

        try:

            print(
                f"Fetching {ticker}"
            )

            ticker_object = yf.Ticker(
                ticker
            )

            data = ticker_object.history(
                period=period,
                auto_adjust=auto_adjust
            )

            # =====================================`========
            # EMPTY DATA CHECK
            # =============================================

            if data.empty:

                print(
                    f"No data found for "
                    f"{ticker}"
                )

                continue

            # =============================================
            # CLEAN DATA
            # =============================================

            data = data.dropna()

            if data.empty:

                print(
                    f"Only NaN data found "
                    f"for {ticker}"
                )

                continue

            # =============================================
            # STORE DATA
            # =============================================

            stock_data[
                symbol
            ] = data

        except Exception as error:

            print(
                f"Error fetching "
                f"{ticker}"
            )

            print(error)

    return stock_data