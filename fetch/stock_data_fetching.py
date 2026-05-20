# -*- coding: utf-8 -*-
"""
Created on Wed May 20 22:09:34 2026

@author: mohak
"""

from __future__ import annotations

import logging
from typing import Dict

import pandas as pd
import yfinance as yf

# =========================================================
# LOGGER
# =========================================================

logger = logging.getLogger(__name__)

# =========================================================
# CONSTANTS
# =========================================================

DATA_PERIOD = "3mo"
CLOSE_COLUMN = "Close"

# =========================================================
# LOAD MASTER UNIVERSE
# =========================================================

def load_master_universe(
    file_path: str
) -> pd.DataFrame:

    dataframe = pd.read_csv(file_path)

    dataframe["Symbol"] = (
        dataframe["Symbol"]
        .astype(str)
        .str.strip()
    )

    dataframe.drop_duplicates(
        subset=["Symbol"],
        inplace=True
    )

    dataframe.reset_index(
        drop=True,
        inplace=True
    )

    logger.info(
        "Unique stocks loaded: %s",
        len(dataframe)
    )

    return dataframe

# =========================================================
# FETCH ALL STOCK DATA
# =========================================================

def fetch_all_stock_data(
    master_dataframe: pd.DataFrame
) -> Dict[str, pd.DataFrame]:

    stock_data = {}

    symbols = (
        master_dataframe["Symbol"]
        .tolist()
    )

    for symbol in symbols:

        ticker = symbol + ".NS"

        try:

            logger.info(
                "Fetching: %s",
                ticker
            )

            data = yf.download(
                ticker,
                period=DATA_PERIOD,
                progress=False,
                auto_adjust=True
            )

            if data.empty:

                logger.warning(
                    "No data for %s",
                    ticker
                )

                continue

            standardized_data = data[
                [CLOSE_COLUMN]
            ].copy()

            standardized_data.columns = [
                CLOSE_COLUMN
            ]

            stock_data[symbol] = (
                standardized_data
            )

        except Exception as error:

            logger.error(
                "Failed fetching %s | %s",
                ticker,
                error
            )

    return stock_data