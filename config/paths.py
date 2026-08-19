# -*- coding: utf-8 -*-
"""
Created on Sun Jul  5 11:27:45 2026

@author: mohak
"""

from pathlib import Path


# ======================================================================
# STOCK_SCANNER REPOSITORY
# ======================================================================

PROJECT_ROOT = (
    Path(__file__).resolve().parents[1]
)


# ======================================================================
# STOCK_SCANNER_DATA REPOSITORY
# ======================================================================
#
# GitHub Actions:
#
# STOCK_SCANNER/
#     ├── config/
#     ├── processing/
#     └── STOCK_SCANNER_DATA/
#
#
# Local development:
#
# STOCK_SCANNER/
#     ├── config/
#     ├── processing/
#     └── ...
#
# STOCK_SCANNER_DATA/
#
# Therefore we support both locations.
# ======================================================================


GITHUB_DATA_REPOSITORY = (
    PROJECT_ROOT
    / "STOCK_SCANNER_DATA"
)


LOCAL_DATA_REPOSITORY = (
    PROJECT_ROOT.parent
    / "STOCK_SCANNER_DATA"
)


if GITHUB_DATA_REPOSITORY.exists():

    DATA_REPOSITORY = (
        GITHUB_DATA_REPOSITORY
    )


elif LOCAL_DATA_REPOSITORY.exists():

    DATA_REPOSITORY = (
        LOCAL_DATA_REPOSITORY
    )


else:

    raise FileNotFoundError(
        "STOCK_SCANNER_DATA repository not found.\n"
        f"Checked:\n"
        f"  {GITHUB_DATA_REPOSITORY}\n"
        f"  {LOCAL_DATA_REPOSITORY}"
    )


# ======================================================================
# RAW DATA
# ======================================================================

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


# ======================================================================
# PROCESSED DATA
# ======================================================================

PROCESSED_DIRECTORY = (
    DATA_REPOSITORY
    / "processed"
)


PROCESSED_BHAVCOPY_DIRECTORY = (
    PROCESSED_DIRECTORY
    / "bhavcopy"
)


# ======================================================================
# ANALYSIS
# ======================================================================

ANALYSIS_DIRECTORY = (
    DATA_REPOSITORY
    / "analysis"
)


MASTER_UNIVERSE_FILE = (
    DATA_REPOSITORY
    / "master_universe.csv"
)


FINAL_RECOMMENDATIONS_FOLDER = (
    DATA_REPOSITORY
    / "final_recommendations"
)


STRATEGIES_FOLDER = (
    DATA_REPOSITORY
    / "strategies"
)


REPORT_FOLDER = (
    DATA_REPOSITORY
    / "analysis"
    / "reports"
)


# ======================================================================
# BACKTESTING
# ======================================================================

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


# ======================================================================
# RESEARCH
# ======================================================================

RESEARCH_FOLDER = (
    DATA_REPOSITORY
    / "research"
)


# ======================================================================
# RESEARCH MARKET CONTEXT
# ======================================================================
#
# Deliberately separate from the backtesting market-data cache.
# ======================================================================

RESEARCH_MARKET_CONTEXT_FOLDER = (
    RESEARCH_FOLDER
    / "market_context"
)


RESEARCH_MARKET_CONTEXT_INDICES_FOLDER = (
    RESEARCH_MARKET_CONTEXT_FOLDER
    / "indices"
)


RESEARCH_MARKET_CONTEXT_SECTOR_INDICES_FOLDER = (
    RESEARCH_MARKET_CONTEXT_FOLDER
    / "sector_indices"
)


RESEARCH_MARKET_CONTEXT_LOGS_FOLDER = (
    RESEARCH_MARKET_CONTEXT_FOLDER
    / "logs"
)


# ======================================================================
# DEBUG
# ======================================================================

if __name__ == "__main__":

    print(
        "\n"
        + "=" * 70
    )

    print(
        "STOCK SCANNER PATH CONFIGURATION"
    )

    print(
        "=" * 70
    )

    print(
        "\nPROJECT ROOT:"
    )

    print(
        PROJECT_ROOT
    )

    print(
        "\nDATA REPOSITORY:"
    )

    print(
        DATA_REPOSITORY
    )

    print(
        "\nMASTER UNIVERSE:"
    )

    print(
        MASTER_UNIVERSE_FILE
    )

    print(
        "\nRAW BHAVCOPY:"
    )

    print(
        RAW_BHAVCOPY_DIRECTORY
    )

    print(
        "\nPROCESSED BHAVCOPY:"
    )

    print(
        PROCESSED_BHAVCOPY_DIRECTORY
    )

    print(
        "\nRESEARCH:"
    )

    print(
        RESEARCH_FOLDER
    )

    print(
        "\nRESEARCH MARKET CONTEXT:"
    )

    print(
        RESEARCH_MARKET_CONTEXT_FOLDER
    )

    print(
        "\nRESEARCH MARKET CONTEXT INDICES:"
    )

    print(
        RESEARCH_MARKET_CONTEXT_INDICES_FOLDER
    )

    print(
        "\nRESEARCH MARKET CONTEXT SECTOR INDICES:"
    )

    print(
        RESEARCH_MARKET_CONTEXT_SECTOR_INDICES_FOLDER
    )

    print(
        "\nRESEARCH MARKET CONTEXT LOGS:"
    )

    print(
        RESEARCH_MARKET_CONTEXT_LOGS_FOLDER
    )

    print(
        "\n"
        + "=" * 70
    )