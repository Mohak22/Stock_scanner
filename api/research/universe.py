
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
    Construct the historical all-stocks universe from dated NSE
    equity bhavcopy records.

    A symbol is eligible on dates for which its EQ record exists
    in the historical data. The current research universe is never
    used to filter historical membership.

    This is a historical-tradability proxy, not an official
    listing/delisting master.
    """

    required_columns = {
        "SYMBOL",
        "SERIES",
        "TIMESTAMP",
    }

    missing_columns = required_columns - set(dataframe.columns)

    if missing_columns:
        raise ValueError(
            "Historical bhavcopy data is missing required columns: "
            f"{sorted(missing_columns)}"
        )

    result = dataframe.copy()

    result["TIMESTAMP"] = pd.to_datetime(
        result["TIMESTAMP"],
        errors="coerce",
    ).dt.normalize()

    result["SYMBOL"] = (
        result["SYMBOL"]
        .where(result["SYMBOL"].notna(), "")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    result["SERIES"] = (
        result["SERIES"]
        .where(result["SERIES"].notna(), "")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    valid_rows = (
        result["TIMESTAMP"].notna()
        & result["SYMBOL"].ne("")
        & result["SERIES"].eq("EQ")
    )

    result = result.loc[valid_rows].copy()

    if result.empty:
        raise ValueError(
            "No valid historical EQ-bhavcopy symbol/date records "
            "remain. Point-in-time research cannot continue."
        )

    return result.reset_index(drop=True)


def validate_bhavcopy_session_coverage(
    observed_dates,
    expected_dates,
) -> None:
    """
    Fail closed when historical bhavcopy lacks a session represented
    in the NIFTY 50 benchmark.

    This detects missing whole sessions. It cannot independently
    prove that every individual stock record is present.
    """

    observed = pd.DatetimeIndex(
        pd.to_datetime(
            list(observed_dates),
            errors="coerce",
        )
    ).dropna().normalize()

    expected = pd.DatetimeIndex(
        pd.to_datetime(
            list(expected_dates),
            errors="coerce",
        )
    ).dropna().normalize()

    observed_set = set(observed)
    expected_set = set(expected)

    missing_dates = sorted(expected_set - observed_set)

    if missing_dates:
        examples = [
            date.strftime("%Y-%m-%d")
            for date in missing_dates[:10]
        ]

        raise ValueError(
            f"Historical bhavcopy is missing {len(missing_dates)} "
            "benchmark trading session(s). "
            f"First missing dates: {examples}. "
            "Repair or verify the archive before trusting this "
            "point-in-time research result."
        )


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