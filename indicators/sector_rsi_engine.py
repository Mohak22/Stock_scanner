# -*- coding: utf-8 -*-
"""
Created on Wed May 20 21:39:34 2026

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
    """
    Calculate RSI using exponential weighted averages.

    Args:
        price_series: Close price series
        period: RSI lookback period

    Returns:
        RSI series
    """

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
# CALCULATE SECTOR RSI
# =========================================================

def calculate_sector_rsi(
    sector_data: Dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """
    Calculate RSI values for all sectors.

    Args:
        sector_data:
            Dictionary containing sector dataframes

    Returns:
        Ranked sector RSI dataframe
    """

    results = []

    for sector, dataframe in sector_data.items():

        try:

            close_prices = dataframe[
                CLOSE_COLUMN
            ]
            if len(close_prices) < 20:

                logger.warning(
                "Insufficient data for RSI calculation: %s",
                sector
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

            results.append({
                "Sector": sector,
                "RSI_9": round(rsi_9, 2),
                "RSI_14": round(rsi_14, 2)
            })
            if pd.isna(rsi_9) or pd.isna(rsi_14):
                logger.warning(
                "NaN RSI detected for %s",
                sector
                )
                continue
        except Exception as error:

            logger.error(
                "RSI calculation failed for %s | %s",
                sector,
                error
            )

    rsi_dataframe = pd.DataFrame(
        results
    )

    rsi_dataframe.sort_values(
        by="RSI_14",
        ascending=True,
        inplace=True
    )

    rsi_dataframe.reset_index(
        drop=True,
        inplace=True
    )

    return rsi_dataframe