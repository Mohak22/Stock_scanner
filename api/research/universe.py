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

import pandas as pd

from api.data.github_data import ResearchDataRepository


RESEARCH_UNIVERSE_PATH = "research_universe.csv"


def load_research_universe_dataframe() -> pd.DataFrame:
    repository = ResearchDataRepository()

    dataframe = repository.load_csv(RESEARCH_UNIVERSE_PATH)

    if "SYMBOL" not in dataframe.columns:
        raise ValueError(
            "research_universe.csv must contain a SYMBOL column."
        )

    dataframe["SYMBOL"] = (
        dataframe["SYMBOL"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    dataframe = dataframe[
        dataframe["SYMBOL"].ne("")
    ].copy()

    dataframe = dataframe.drop_duplicates(
        subset=["SYMBOL"]
    ).reset_index(drop=True)

    return dataframe


def get_research_universe_symbols() -> set[str]:
    dataframe = load_research_universe_dataframe()

    return set(dataframe["SYMBOL"].tolist())


def load_research_universe() -> list[dict]:
    dataframe = load_research_universe_dataframe()

    dataframe = dataframe.fillna("")

    return dataframe.to_dict(orient="records")


def get_research_universe() -> dict:
    rows = load_research_universe()

    return {
        "universe": rows,
        "total_stocks": len(rows),
    }