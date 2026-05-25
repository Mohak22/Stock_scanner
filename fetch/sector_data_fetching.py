# -*- coding: utf-8 -*-
"""
Created on Sun May 17 16:03:05 2026

@author: mohak
"""

from __future__ import annotations

import logging
from typing import Dict, List
from typing import Optional
import pandas as pd
import yfinance as yf
from pydantic import BaseModel, field_validator

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
# PYDANTIC SCHEMA
# =========================================================

class UniverseSchema(BaseModel):

    Symbol: str
    sector: Optional[str] = None

    @field_validator("Symbol", "sector")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("Field cannot be empty.")

        return cleaned_value

# =========================================================
# LOAD MASTER UNIVERSE
# =========================================================

def load_master_universe(
    file_path: str
) -> pd.DataFrame:

    dataframe = pd.read_csv(file_path)

    dataframe = (
        dataframe.where(
        pd.notnull(dataframe),
        None
        )
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

    records = dataframe[
        ["Symbol", "sector"]
    ].to_dict("records")

    for record in records:
        UniverseSchema(**record)

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

    return dataframe["sector"].unique().tolist()

# =========================================================
# FETCH YAHOO INDEX
# =========================================================

def fetch_yahoo_sector_index(
    ticker: str
) -> pd.DataFrame:

    data = yf.download(
        ticker,
        period=DATA_PERIOD,
        progress=False,
        auto_adjust=True
    )

    if data.empty:
        raise ValueError(
            f"No data returned for {ticker}"
        )

    standardized_data = data[
        [CLOSE_COLUMN]
    ].copy()

    standardized_data.columns = [
        CLOSE_COLUMN
    ]

    return (
        standardized_data[
            CLOSE_COLUMN
        ].dropna()
        )

# =========================================================
# FETCH STOCK CLOSE PRICES
# =========================================================

# =========================================================
# FETCH STOCK CLOSE PRICES
# =========================================================

def fetch_stock_close_prices(
    tickers: List[str]
) -> pd.DataFrame:

    try:

        data = yf.download(
            tickers,
            period=DATA_PERIOD,
            progress=False,
            auto_adjust=True,
            group_by="ticker"
        )

        close_price_dict = {}

        for ticker in tickers:

            try:

                close_price_dict[ticker] = (
                    data[ticker][CLOSE_COLUMN]
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
# BUILD SYNTHETIC SECTOR
# =========================================================

def build_synthetic_sector_index(
    close_prices: pd.DataFrame
) -> pd.Series:

    if close_prices.empty:

        raise ValueError(
            "Empty close price data."
        )

    # =====================================================
    # DAILY RETURNS
    # =====================================================

    daily_returns = (
        close_prices.pct_change()
    )

    # =====================================================
    # AVERAGE SECTOR RETURN
    # =====================================================

    sector_returns = (
        daily_returns.mean(
            axis=1
        )
    )

    # =====================================================
    # SYNTHETIC INDEX
    # =====================================================

    synthetic_close = (
        (1 + sector_returns)
        .cumprod() * 100
    )

    # =====================================================
    # RETURN SERIES ONLY
    # =====================================================

    return synthetic_close.dropna()

# =========================================================
# PROCESS SINGLE SECTOR
# =========================================================

def process_sector(
    sector: str,
    master_dataframe: pd.DataFrame
) -> pd.Series:

    yahoo_ticker = (
        SECTOR_INDEX_MAP.get(sector)
    )

    if yahoo_ticker:

        try:

            logger.info(
                "Fetching official sector index for %s",
                sector
            )

            return fetch_yahoo_sector_index(
                yahoo_ticker
            )

        except Exception as error:

            logger.warning(
                "Official sector fetch failed for %s | %s",
                sector,
                error
            )

    logger.info(
        "Creating synthetic sector for %s",
        sector
    )

    sector_dataframe = master_dataframe[
        master_dataframe["sector"] == sector
    ]

    tickers = (
        sector_dataframe["Symbol"]
        + ".NS"
    ).tolist()

    close_prices = (
        fetch_stock_close_prices(
            tickers
        )
    )

    return build_synthetic_sector_index(
        close_prices
    )

# =========================================================
# FETCH ALL SECTORS
# =========================================================

def fetch_sector_data(
    master_dataframe: pd.DataFrame
) -> Dict[str, pd.DataFrame]:

    sector_data: Dict[
        str,
        pd.DataFrame
    ] = {}

    sectors = extract_unique_sectors(
        master_dataframe
    )

    for sector in sectors:

        try:

            sector_data[sector] = (
                process_sector(
                    sector,
                    master_dataframe
                )
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