# -*- coding: utf-8 -*-
"""
Created on Wed May 20 22:21:25 2026

@author: mohak
"""

from __future__ import annotations

import logging
from typing import Dict

import pandas as pd

# =========================================================
# LOGGER
# =========================================================

logger = logging.getLogger(__name__)

# =========================================================
# CONSTANTS
# =========================================================

CLOSE_COLUMN = "Close"

# =========================================================
# RSI CALCULATION
# =========================================================

def calculate_rsi(
    price_series: pd.Series,
    period: int
) -> pd.Series:

    delta = price_series.diff()

    gains = delta.clip(lower=0)

    losses = -delta.clip(upper=0)

    average_gain = gains.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    average_loss = losses.ewm(
        alpha=1 / period,
        adjust=False
    ).mean()

    relative_strength = (
        average_gain / average_loss
    )

    rsi = 100 - (
        100 / (1 + relative_strength)
    )

    return rsi

# =========================================================
# CALCULATE STOCK RSI
# =========================================================

def calculate_stock_rsi(
    stock_data: Dict[str, pd.DataFrame]
) -> pd.DataFrame:

    results = []

    for stock, dataframe in stock_data.items():

        try:

            close_prices = dataframe[
                CLOSE_COLUMN
            ]

            if len(close_prices) < 20:

                logger.warning(
                    "Insufficient data for %s",
                    stock
                )

                continue

            rsi_9 = calculate_rsi(
                close_prices,
                period=9
            ).iloc[-1]

            rsi_14 = calculate_rsi(
                close_prices,
                period=14
            ).iloc[-1]

            if (
                pd.isna(rsi_9)
                or
                pd.isna(rsi_14)
            ):
                continue

            results.append({

                "Stock": stock,

                "RSI_9": round(
                    rsi_9,
                    2
                ),

                "RSI_14": round(
                    rsi_14,
                    2
                )
            })

        except Exception as error:

            logger.error(
                "RSI failed for %s | %s",
                stock,
                error
            )

    rsi_dataframe = pd.DataFrame(
        results
    )

    return rsi_dataframe

# =========================================================
# FILTER OVERSOLD STOCKS
# =========================================================

def filter_oversold_stocks(
    rsi_dataframe: pd.DataFrame
) -> pd.DataFrame:

    filtered_dataframe = rsi_dataframe[
        (
            rsi_dataframe["RSI_9"] < 30
        )
        |
        (
            rsi_dataframe["RSI_14"] < 30
        )
    ].copy()

    filtered_dataframe.sort_values(
        by="RSI_14",
        ascending=True,
        inplace=True
    )

    filtered_dataframe.reset_index(
        drop=True,
        inplace=True
    )

    return filtered_dataframe