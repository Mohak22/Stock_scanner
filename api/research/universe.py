
from __future__ import annotations

# -*- coding: utf-8 -*-
"""
Created on Sun Aug 30 13:25:46 2026

@author: mohak
"""

"""
Research Universe API

Supported research universes:

    all_stocks
    macro_sector
    sector
    industry
    basic_industry
    major_stocks
    symbols

Major Stocks
------------

Major Stocks is represented by the current Nifty 500
constituent universe.

The Nifty 500 constituent list is stored separately from
research_universe.csv so that the universe definition is explicit
and reproducible.
"""

import pandas as pd

from api.data.github_data import ResearchDataRepository


RESEARCH_UNIVERSE_PATH = (
    "research_universe.csv"
)

POINT_IN_TIME_UNIVERSE_PATH = (
    "research_universe_history.csv"
)

MAJOR_STOCKS_UNIVERSE_PATH = (
    "raw/nifty_500_universe.csv"
)


def _normalise_symbols(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:

    if "SYMBOL" not in dataframe.columns:

        raise ValueError(
            "Research universe data must contain a SYMBOL column."
        )

    dataframe = dataframe.copy()

    dataframe["SYMBOL"] = (
        dataframe["SYMBOL"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    dataframe = dataframe[
        dataframe["SYMBOL"].ne("")
    ].copy()

    return dataframe


def load_research_universe_dataframe() -> pd.DataFrame:

    repository = ResearchDataRepository()

    dataframe = repository.load_csv(
        RESEARCH_UNIVERSE_PATH
    )

    dataframe = _normalise_symbols(
        dataframe
    )

    dataframe = dataframe.drop_duplicates(
        subset=["SYMBOL"]
    ).reset_index(drop=True)

    return dataframe


def load_major_stocks_universe_dataframe() -> pd.DataFrame:

    repository = ResearchDataRepository()

    dataframe = repository.load_csv(
        MAJOR_STOCKS_UNIVERSE_PATH
    )

    dataframe = _normalise_symbols(
        dataframe
    )

    dataframe = dataframe.drop_duplicates(
        subset=["SYMBOL"]
    ).reset_index(drop=True)

    if dataframe.empty:

        raise ValueError(
            "Nifty 500 universe is empty."
        )

    return dataframe


def load_point_in_time_universe_dataframe() -> pd.DataFrame:

    repository = ResearchDataRepository()

    dataframe = repository.load_csv(
        POINT_IN_TIME_UNIVERSE_PATH
    )

    dataframe = _normalise_symbols(
        dataframe
    )

    required_columns = {
        "EFFECTIVE_FROM",
        "EFFECTIVE_TO",
    }

    missing_columns = (
        required_columns
        - set(dataframe.columns)
    )

    if missing_columns:

        raise ValueError(
            "Point-in-time universe is missing required "
            f"columns: {sorted(missing_columns)}"
        )

    dataframe["EFFECTIVE_FROM"] = pd.to_datetime(
        dataframe["EFFECTIVE_FROM"],
        errors="coerce",
    ).dt.normalize()

    dataframe["EFFECTIVE_TO"] = pd.to_datetime(
        dataframe["EFFECTIVE_TO"],
        errors="coerce",
    ).dt.normalize()

    if dataframe[
        ["EFFECTIVE_FROM", "EFFECTIVE_TO"]
    ].isna().any().any():

        raise ValueError(
            "Point-in-time universe contains invalid "
            "EFFECTIVE_FROM or EFFECTIVE_TO dates."
        )

    invalid_ranges = (
        dataframe["EFFECTIVE_FROM"]
        > dataframe["EFFECTIVE_TO"]
    )

    if invalid_ranges.any():

        raise ValueError(
            "Point-in-time universe contains membership "
            "ranges where EFFECTIVE_FROM is after EFFECTIVE_TO."
        )

    duplicate_membership = dataframe.duplicated(
        subset=[
            "SYMBOL",
            "EFFECTIVE_FROM",
            "EFFECTIVE_TO",
        ],
        keep=False,
    )

    if duplicate_membership.any():

        raise ValueError(
            "Point-in-time universe contains duplicate "
            "membership intervals."
        )

    ordered = dataframe.sort_values(
        [
            "SYMBOL",
            "EFFECTIVE_FROM",
            "EFFECTIVE_TO",
        ]
    ).copy()

    ordered["PREVIOUS_EFFECTIVE_TO"] = (
        ordered
        .groupby("SYMBOL")["EFFECTIVE_TO"]
        .shift(1)
    )

    overlapping = (
        ordered["PREVIOUS_EFFECTIVE_TO"].notna()
        & (
            ordered["EFFECTIVE_FROM"]
            <= ordered["PREVIOUS_EFFECTIVE_TO"]
        )
    )

    if overlapping.any():

        raise ValueError(
            "Point-in-time universe contains overlapping "
            "membership intervals for at least one symbol."
        )

    ordered = ordered.drop(
        columns=["PREVIOUS_EFFECTIVE_TO"]
    )

    return ordered.reset_index(drop=True)


def get_research_universe_symbols() -> set[str]:

    dataframe = (
        load_research_universe_dataframe()
    )

    return set(
        dataframe["SYMBOL"].tolist()
    )


def load_research_universe() -> list[dict]:

    dataframe = (
        load_research_universe_dataframe()
    )

    dataframe = dataframe.fillna("")

    return dataframe.to_dict(
        orient="records"
    )


def get_research_universe() -> dict:

    rows = load_research_universe()

    major_stocks = (
        load_major_stocks_universe_dataframe()
    )

    return {
        "universe": rows,
        "total_stocks": len(rows),
        "major_stocks_total": len(
            major_stocks
        ),
        "membership_basis": (
            "current_snapshot_not_point_in_time"
        ),
    }


def apply_current_snapshot_universe(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:

    universe = (
        load_research_universe_dataframe()
    )

    symbols = set(
        universe["SYMBOL"].tolist()
    )

    return dataframe[
        dataframe["SYMBOL"].isin(symbols)
    ].copy()


def apply_major_stocks_universe(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:

    universe = (
        load_major_stocks_universe_dataframe()
    )

    symbols = set(
        universe["SYMBOL"].tolist()
    )

    return dataframe[
        dataframe["SYMBOL"].isin(symbols)
    ].copy()



def apply_point_in_time_universe(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build the historical all-stocks universe from dated bhavcopy rows.

    Each symbol is eligible only on dates for which it has a record
    in the historical bhavcopy data supplied to this function.

    Important:
    - Does not filter against today's research_universe.csv.
    - Does not require research_universe_history.csv.
    - Depends on historical bhavcopy coverage being sufficiently complete.
    - Does not infer historical sector classifications or index membership.
    """

    required_columns = {
        "SYMBOL",
        "TIMESTAMP",
    }

    missing_columns = required_columns - set(dataframe.columns)

    if missing_columns:
        raise ValueError(
            "Historical bhavcopy data is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    result = dataframe.copy()

    # Normalize dates so universe eligibility is evaluated by trading day.
    result["TIMESTAMP"] = (
        pd.to_datetime(
            result["TIMESTAMP"],
            errors="coerce",
        )
        .dt.normalize()
    )

    # Normalize symbols without turning missing values into the literal
    # string "NAN".
    result["SYMBOL"] = (
        result["SYMBOL"]
        .where(result["SYMBOL"].notna(), "")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    valid_rows = (
        result["TIMESTAMP"].notna()
        & result["SYMBOL"].ne("")
    )

    result = result.loc[valid_rows].copy()

    if result.empty:
        raise ValueError(
            "No valid symbol/date records remain in historical bhavcopy "
            "data. Point-in-time universe construction cannot continue."
        )

    # Deliberately do not intersect with the current research universe.
    # The dated bhavcopy rows are the source of historical eligibility.
    return result.reset_index(drop=True)


def apply_research_universe(
    dataframe: pd.DataFrame,
    membership_basis: str,
) -> pd.DataFrame:

    if membership_basis == "current_snapshot":

        return apply_current_snapshot_universe(
            dataframe
        )

    if membership_basis == "point_in_time":

        return apply_point_in_time_universe(
            dataframe
        )

    raise ValueError(
        "Unsupported universe membership basis: "
        f"{membership_basis}"
    )