# -*- coding: utf-8 -*-
"""
Created on Sun Jul  5 11:27:45 2026

@author: mohak
"""

# -*- coding: utf-8 -*-

from pathlib import Path


# STOCK_SCANNER repository
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Parent folder containing both repositories
WORKSPACE_ROOT = PROJECT_ROOT.parent

# STOCK_SCANNER_DATA repository
DATA_REPOSITORY = (
    WORKSPACE_ROOT
    / "STOCK_SCANNER_DATA"
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