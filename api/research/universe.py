# -*- coding: utf-8 -*-
"""
Created on Sun Aug 30 13:25:46 2026

@author: mohak
"""

# -*- coding: utf-8 -*-
"""
Research Universe API

Purpose:
    Provide the Strategy Inventor with the available research universe.

Data source:
    Private GitHub STOCK_SCANNER_DATA repository.

Important:
    This module does not calculate features or run strategies.
    It only retrieves the research universe.
"""

from api.data.github_data import (
    ResearchDataRepository
)


# ======================================================================
# CONSTANTS
# ======================================================================

RESEARCH_UNIVERSE_PATH = (
    "research_universe.csv"
)


# ======================================================================
# LOAD RESEARCH UNIVERSE
# ======================================================================

def load_research_universe() -> list[dict]:

    repository = ResearchDataRepository()

    dataframe = repository.load_csv(
        RESEARCH_UNIVERSE_PATH
    )

    dataframe = dataframe.fillna("")

    return dataframe.to_dict(
        orient="records"
    )


# ======================================================================
# UNIVERSE SUMMARY
# ======================================================================

def get_research_universe() -> dict:

    rows = load_research_universe()

    return {
        "universe": rows,
        "total_stocks": len(rows)
    }