# -*- coding: utf-8 -*-
"""
Central path configuration for STOCK_SCANNER.

The project expects STOCK_SCANNER_DATA to be available
inside the STOCK_SCANNER project directory.

Local:

    STOCK_SCANNER/
        STOCK_SCANNER_DATA/

GitHub Actions:

    Stock_scanner/
        Stock_scanner/
            STOCK_SCANNER_DATA/

This file should be the single source of truth for
all data-repository paths.
"""

from pathlib import Path


# ======================================================================
# PROJECT ROOT
# ======================================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ======================================================================
# DATA REPOSITORY
# ======================================================================

DATA_REPOSITORY = (
    PROJECT_ROOT
    / "STOCK_SCANNER_DATA"
)


# ======================================================================
# RAW DATA
# ======================================================================

RAW_DATA_DIRECTORY = (
    DATA_REPOSITORY
    / "raw"
)


RAW_BHAVCOPY_DIRECTORY = (
    RAW_DATA_DIRECTORY
    / "nse"
    / "bhavcopy"
)


RAW_MTO_DIRECTORY = (
    RAW_DATA_DIRECTORY
    / "nse"
    / "mto"
)


# ======================================================================
# PROCESSED DATA
# ======================================================================

PROCESSED_DATA_DIRECTORY = (
    DATA_REPOSITORY
    / "processed"
)


PROCESSED_BHAVCOPY_DIRECTORY = (
    PROCESSED_DATA_DIRECTORY
    / "bhavcopy"
)


# ======================================================================
# MASTER UNIVERSE
# ======================================================================

MASTER_UNIVERSE_FILE = (
    DATA_REPOSITORY
    / "master_universe.csv"
)


# ======================================================================
# RESEARCH UNIVERSE
# ======================================================================

RESEARCH_UNIVERSE_FILE = (
    DATA_REPOSITORY
    / "research_universe.csv"
)


# ======================================================================
# RESEARCH DATA
# ======================================================================

RESEARCH_DIRECTORY = (
    DATA_REPOSITORY
    / "research"
)


# ======================================================================
# HISTORICAL STOCK MARKET DATA
# ======================================================================

HISTORICAL_MARKET_DATA_DIRECTORY = (
    RESEARCH_DIRECTORY
    / "historical_market_data"
)


HISTORICAL_MARKET_DATA_RAW_DIRECTORY = (
    HISTORICAL_MARKET_DATA_DIRECTORY
    / "raw"
)


HISTORICAL_MARKET_DATA_LOG_DIRECTORY = (
    HISTORICAL_MARKET_DATA_DIRECTORY
    / "logs"
)


# ======================================================================
# MARKET CONTEXT
# ======================================================================

MARKET_CONTEXT_DIRECTORY = (
    RESEARCH_DIRECTORY
    / "market_context"
)


# ======================================================================
# SECTOR DATA
# ======================================================================

SECTOR_DATA_DIRECTORY = (
    RESEARCH_DIRECTORY
    / "sector_data"
)


# ======================================================================
# NSE REFERENCE DATA
# ======================================================================

REFERENCE_DATA_DIRECTORY = (
    RESEARCH_DIRECTORY
    / "reference_data"
)


# ======================================================================
# OPTIONAL: CREATE REQUIRED DIRECTORIES
# ======================================================================

RAW_BHAVCOPY_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)

RAW_MTO_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)

PROCESSED_BHAVCOPY_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)

RESEARCH_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)

HISTORICAL_MARKET_DATA_RAW_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)

HISTORICAL_MARKET_DATA_LOG_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)

MARKET_CONTEXT_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)

SECTOR_DATA_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True

)

REFERENCE_DATA_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
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
        f"\nPROJECT_ROOT:\n"
        f"{PROJECT_ROOT}"
    )

    print(
        f"\nDATA_REPOSITORY:\n"
        f"{DATA_REPOSITORY}"
    )

    print(
        f"\nMASTER_UNIVERSE_FILE:\n"
        f"{MASTER_UNIVERSE_FILE}"
    )

    print(
        f"\nRESEARCH_UNIVERSE_FILE:\n"
        f"{RESEARCH_UNIVERSE_FILE}"
    )

    print(
        f"\nRAW_BHAVCOPY_DIRECTORY:\n"
        f"{RAW_BHAVCOPY_DIRECTORY}"
    )

    print(
        f"\nRAW_MTO_DIRECTORY:\n"
        f"{RAW_MTO_DIRECTORY}"
    )

    print(
        f"\nPROCESSED_BHAVCOPY_DIRECTORY:\n"
        f"{PROCESSED_BHAVCOPY_DIRECTORY}"
    )

    print(
        f"\nHISTORICAL_MARKET_DATA_RAW_DIRECTORY:\n"
        f"{HISTORICAL_MARKET_DATA_RAW_DIRECTORY}"
    )

    print(
        "\n"
        + "=" * 70
    )