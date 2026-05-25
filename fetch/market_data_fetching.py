# -*- coding: utf-8 -*-
"""
Created on Sun May 24 11:22:24 2026

@author: mohak
"""

from __future__ import annotations

from typing import Dict

import time

import pandas as pd
import yfinance as yf

# =========================================================
# MARKET INDEX MAP
# =========================================================

MARKET_INDEX_MAP = {

    "NIFTY50": "^NSEI",

    "MIDCAP":
        "NIFTY_MIDCAP_100.NS",

    "BANKNIFTY": "^NSEBANK"
}

# =========================================================
# FETCH SINGLE MARKET
# =========================================================

def fetch_single_market_data(
    market_name: str,
    ticker: str
) -> tuple[str, pd.Series]:

    max_retries = 3

    for attempt in range(
        1,
        max_retries + 1
    ):

        try:

            print(
                f"Fetching {market_name} "
                f"(Attempt {attempt})"
            )

            ticker_object = yf.Ticker(
               ticker
            )

            data = ticker_object.history(
                 period="3mo",
                 auto_adjust=True
                 )

            # =====================================
            # EMPTY DATA CHECK
            # =====================================

            if data.empty:

                raise ValueError(
                    f"No data found "
                    f"for {market_name}"
                )

            # =====================================
            # CLOSE PRICE EXTRACTION
            # =====================================

            close_prices = data["Close"]

            # =====================================
            # FORCE CLEAN SERIES
            # =====================================

            if isinstance(
                close_prices,
                pd.DataFrame
            ):

                close_prices = (
                    close_prices.iloc[:, 0]
                )

            close_prices = (
                close_prices.dropna()
            )

            # =====================================
            # FINAL VALIDATION
            # =====================================

            if close_prices.empty:

                raise ValueError(
                    f"Empty close prices "
                    f"for {market_name}"
                )

            print(
                f"{market_name} fetched "
                f"successfully"
            )

            return (
                market_name,
                close_prices
            )

        except Exception as error:

            print(
                f"Error fetching "
                f"{market_name}"
            )

            print(error)

            # =====================================
            # RETRY DELAY
            # =====================================

            time.sleep(2)

    # =============================================
    # FINAL FAILURE
    # =============================================

    print(
        f"{market_name} failed after "
        f"{max_retries} attempts"
    )

    return (
        market_name,
        pd.Series(dtype=float)
    )

# =========================================================
# FETCH ALL MARKET DATA
# =========================================================

def fetch_market_data(
) -> Dict[str, pd.Series]:

    market_data = {}

    for (
        market_name,
        ticker
    ) in MARKET_INDEX_MAP.items():

        (
            fetched_market_name,
            close_prices
        ) = fetch_single_market_data(
            market_name,
            ticker
        )

        if not close_prices.empty:

            market_data[
                fetched_market_name
            ] = close_prices

    return market_data