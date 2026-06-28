# -*- coding: utf-8 -*-
"""
Created on Sun May 17 16:03:05 2026

@author: mohak
"""

from __future__ import annotations

import logging
from typing import Dict, List

import pandas as pd
import yfinance as yf


# =========================================================
# LOGGING
# =========================================================

logger = logging.getLogger(__name__)


# =========================================================
# CONSTANTS
# =========================================================

DATA_PERIOD = "3mo"

CLOSE_COLUMN = "Close"

SECTOR_INDEX_MAP: Dict[str, str] = {
    "AUTO": "^CNXAUTO",
    "BANK": "^NSEBANK",
    "FMCG": "^CNXFMCG",
    "IT": "^CNXIT",
    "MEDIA": "^CNXMEDIA",
    "METAL": "^CNXMETAL",
    "PHARMA": "^CNXPHARMA",
    "REALTY": "^CNXREALTY",
    "ENERGY": "^CNXENERGY",
    "INFRA": "^CNXINFRA",
    "PSUBANK": "^CNXPSUBANK",
    "PRIVATEBANK": "NIFTY_PVT_BANK.NS",
    "CEMENT": "NIFTY_CEMENT.NS",
    "CHEMICALS": "NIFTY_CHEMICALS.NS",
    "FINANCE": "NIFTY_FIN_SERVICE.NS",
    "HEALTHCARE": "NIFTY_HEALTHCARE.NS",
    "HOUSING": "NIFTY_HEALTHCARE.NS",
    "PSE": "^CNXPSE"
}


# =========================================================
# LOAD MASTER UNIVERSE
# =========================================================

def load_master_universe(
    file_path: str
) -> pd.DataFrame:

    dataframe = pd.read_csv(
        file_path
    )

    dataframe["Symbol"] = (
        dataframe["Symbol"]
        .astype(str)
        .str.strip()
    )

    dataframe["sector"] = (
        dataframe["sector"]
        .astype(str)
        .str.strip()
    )

    logger.info(
        "Master universe loaded successfully."
    )

    return dataframe


# =========================================================
# EXTRACT UNIQUE SECTORS
# =========================================================

def extract_unique_sectors(
    dataframe: pd.DataFrame
) -> List[str]:

    return (
        dataframe["sector"]
        .unique()
        .tolist()
    )


# =========================================================
# FETCH INDEX DATA
# =========================================================

def fetch_index_data(
    ticker: str,
    period: str = DATA_PERIOD
) -> pd.Series:

    data = yf.download(
        ticker,
        period=period,
        progress=False,
        auto_adjust=True
    )

    if data.empty:

        raise ValueError(
            f"No data returned for {ticker}"
        )

    close_prices = data[CLOSE_COLUMN]

    # =====================================
    # FORCE SERIES
    # =====================================

    if isinstance(
        close_prices,
        pd.DataFrame
    ):

        close_prices = (
            close_prices.iloc[:, 0]
        )

    close_prices = (
        close_prices
        .dropna()
    )

    return close_prices


# =========================================================
# FETCH STOCK CLOSE PRICES
# =========================================================

def fetch_stock_close_prices(
    tickers: List[str],
    period: str = DATA_PERIOD
) -> pd.DataFrame:

    try:

        data = yf.download(
            tickers,
            period=period,
            progress=False,
            auto_adjust=True,
            group_by="ticker"
        )

        close_price_dict = {}

        for ticker in tickers:

            try:

                close_price_dict[ticker] = (
                    data[ticker][
                        CLOSE_COLUMN
                    ]
                )

            except Exception:

                logger.warning(
                    "No data for %s",
                    ticker
                )

        close_prices = pd.DataFrame(
            close_price_dict
        )

        close_prices.dropna(
            axis=1,
            how="all",
            inplace=True
        )

        return close_prices

    except Exception as error:

        logger.error(
            "Bulk stock fetch failed | %s",
            error
        )

        return pd.DataFrame()


# =========================================================
# BUILD SYNTHETIC INDEX
# =========================================================

def build_synthetic_index(
    close_prices: pd.DataFrame,
    base_value: float = 100.0
) -> pd.Series:

    if close_prices.empty:

        raise ValueError(
            "Empty close price data."
        )

    daily_returns = (
        close_prices.pct_change()
    )

    basket_returns = (
        daily_returns.mean(
            axis=1
        )
    )

    synthetic_index = (
        (1 + basket_returns)
        .cumprod()
        * base_value
    )

    return (
        synthetic_index
        .dropna()
    )


# =========================================================
# BUILD BASKET DATA
# =========================================================

def build_basket_data(
    tickers: List[str]
) -> pd.Series:

    close_prices = (
        fetch_stock_close_prices(
            tickers=tickers
        )
    )

    return build_synthetic_index(
        close_prices=close_prices
    )


# =========================================================
# PROCESS SINGLE SECTOR
# =========================================================

def process_sector(
    sector: str,
    master_dataframe: pd.DataFrame
) -> pd.Series:

    official_ticker = (
        SECTOR_INDEX_MAP.get(
            sector
        )
    )

    # =====================================================
    # TRY OFFICIAL INDEX
    # =====================================================

    if official_ticker:

        try:

            logger.info(
                "Fetching official index for %s",
                sector
            )

            return fetch_index_data(
                ticker=official_ticker
            )

        except Exception as error:

            logger.warning(
                "Official index failed for %s | %s",
                sector,
                error
            )

    # =====================================================
    # FALLBACK TO SYNTHETIC
    # =====================================================

    logger.info(
        "Building synthetic basket for %s",
        sector
    )

    sector_dataframe = (
        master_dataframe[
            master_dataframe[
                "sector"
            ] == sector
        ]
    )

    tickers = (
        sector_dataframe[
            "Symbol"
        ] + ".NS"
    ).tolist()

    return build_basket_data(
        tickers=tickers
    )


# =========================================================
# FETCH ALL SECTOR DATA
# =========================================================

def fetch_sector_data(
    master_dataframe: pd.DataFrame
) -> Dict[str, pd.Series]:

    sector_data: Dict[
        str,
        pd.Series
    ] = {}

    sectors = (
        extract_unique_sectors(
            master_dataframe
        )
    )

    for sector in sectors:

        try:

            sector_data[
                sector
            ] = process_sector(
                sector=sector,
                master_dataframe=master_dataframe
            )

            logger.info(
                "Sector processed successfully: %s",
                sector
            )

        except Exception as error:

            logger.error(
                "Sector processing failed for %s | %s",
                sector,
                error
            )

    return sector_data