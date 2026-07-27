# -*- coding: utf-8 -*-
"""
Created on Sun Jul  5 11:27:45 2026

@author: mohak
"""

# -*- coding: utf-8 -*-

from pathlib import Path

# STOCK_SCANNER repository
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Possible locations of STOCK_SCANNER_DATA
GITHUB_DATA_REPOSITORY = (
    PROJECT_ROOT
    / "STOCK_SCANNER_DATA"
)

LOCAL_DATA_REPOSITORY = (
    PROJECT_ROOT.parent
    / "STOCK_SCANNER_DATA"
)

if GITHUB_DATA_REPOSITORY.exists():

    DATA_REPOSITORY = GITHUB_DATA_REPOSITORY

elif LOCAL_DATA_REPOSITORY.exists():

    DATA_REPOSITORY = LOCAL_DATA_REPOSITORY

else:

    raise FileNotFoundError(
        "STOCK_SCANNER_DATA repository not found."
    )

# Raw Data
RAW_DATA_DIRECTORY = (
    DATA_REPOSITORY
    / "raw"
)

RAW_NSE_DIRECTORY = (
    RAW_DATA_DIRECTORY
    / "nse"
)

RAW_BHAVCOPY_DIRECTORY = (
    RAW_NSE_DIRECTORY
    / "bhavcopy"
)

# Processed Data
PROCESSED_DIRECTORY = (
    DATA_REPOSITORY
    / "processed"
)

PROCESSED_BHAVCOPY_DIRECTORY = (
    PROCESSED_DIRECTORY
    / "bhavcopy"
)

# Analysis
ANALYSIS_DIRECTORY = (
    DATA_REPOSITORY
    / "analysis"
)

MASTER_UNIVERSE_FILE = (
    DATA_REPOSITORY
    / "master_universe.csv"
)

FINAL_RECOMMENDATIONS_FOLDER = (
    DATA_REPOSITORY / "final_recommendations"
)

STRATEGIES_FOLDER = (
    DATA_REPOSITORY / "strategies"
)

REPORT_FOLDER = (
    DATA_REPOSITORY / "analysis" / "reports"
)

BACKTESTING_FOLDER = (
    DATA_REPOSITORY
    / "backtesting"
)

BACKTEST_RESULTS_FOLDER = (
    BACKTESTING_FOLDER
    / "results"
)

BACKTEST_STRATEGIES_FOLDER = (
    BACKTESTING_FOLDER
    / "strategies"
)

BACKTEST_MARKET_DATA_FOLDER = (
    BACKTESTING_FOLDER
    / "market_data"
)

BACKTEST_NIFTY_FILE = (
    BACKTEST_MARKET_DATA_FOLDER
    / "nifty_50.parquet"
)