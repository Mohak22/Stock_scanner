# -*- coding: utf-8 -*-
"""
Created on Fri Sep  4 11:37:45 2026

@author: mohak
"""

"""
Historical Bhavcopy Loader

Loads processed Bhavcopy parquet files from the
STOCK_SCANNER_DATA repository in chronological order.

This loader is used by the Strategy Inventor research engine.
"""

from pathlib import Path
import re

import pandas as pd


# ======================================================================
# FILE PATTERN
# ======================================================================

BHAVCOPY_PATTERN = re.compile(
    r"sec_bhavdata_full_(\d{8})\.parquet$"
)


# ======================================================================
# EXTRACT DATE FROM FILE NAME
# ======================================================================

def _extract_date(
    file_path: Path
) -> pd.Timestamp | None:

    match = BHAVCOPY_PATTERN.match(
        file_path.name
    )

    if match is None:
        return None

    date_string = match.group(1)

    try:

        return pd.to_datetime(
            date_string,
            format="%d%m%Y"
        )

    except ValueError:

        return None


# ======================================================================
# FIND BHAVCOPY FILES
# ======================================================================

def find_bhavcopy_files(
    directory: Path
) -> list[tuple[pd.Timestamp, Path]]:

    files = []

    for file_path in directory.glob(
        "sec_bhavdata_full_*.parquet"
    ):

        file_date = _extract_date(
            file_path
        )

        if file_date is None:
            continue

        files.append(
            (
                file_date,
                file_path
            )
        )

    # --------------------------------------------------------------
    # IMPORTANT:
    # Sort using the actual date extracted from the filename.
    # --------------------------------------------------------------

    files.sort(
        key=lambda item: item[0]
    )

    return files


# ======================================================================
# LOAD HISTORICAL BHAVCOPY
# ======================================================================

def load_historical_bhavcopy(
    directory: Path,
    start_date: str | pd.Timestamp,
    end_date: str | pd.Timestamp
) -> pd.DataFrame:
    """
    Load Bhavcopy data for a requested historical period.

    Parameters
    ----------
    directory:
        Processed Bhavcopy directory.

    start_date:
        First requested date.

    end_date:
        Last requested date.

    Returns
    -------
    pd.DataFrame
    """

    start = pd.Timestamp(
        start_date
    )

    end = pd.Timestamp(
        end_date
    )

    if start > end:

        raise ValueError(
            "start_date must be on or before end_date."
        )


    # ==================================================================
    # FIND FILES
    # ==================================================================

    available_files = find_bhavcopy_files(
        directory
    )


    # ==================================================================
    # SELECT FILES IN REQUESTED RANGE
    # ==================================================================

    selected_files = [

        (
            file_date,
            file_path
        )

        for file_date, file_path
        in available_files

        if start <= file_date <= end

    ]


    if not selected_files:

        return pd.DataFrame()


    # ==================================================================
    # LOAD FILES
    # ==================================================================

    frames = []

    for file_date, file_path in selected_files:

        dataframe = pd.read_parquet(
            file_path
        )

        frames.append(
            dataframe
        )


    # ==================================================================
    # COMBINE
    # ==================================================================

    result = pd.concat(
        frames,
        ignore_index=True
    )


    # ==================================================================
    # NORMALISE DATE
    # ==================================================================

    if "TIMESTAMP" not in result.columns:

        raise ValueError(
            "Bhavcopy data does not contain TIMESTAMP column."
        )


    result["TIMESTAMP"] = pd.to_datetime(
        result["TIMESTAMP"],
        errors="coerce"
    )


    # ==================================================================
    # NORMALISE SYMBOL
    # ==================================================================

    if "SYMBOL" not in result.columns:

        raise ValueError(
            "Bhavcopy data does not contain SYMBOL column."
        )


    result["SYMBOL"] = (
        result["SYMBOL"]
        .astype(str)
        .str.strip()
        .str.upper()
    )


    # ==================================================================
    # FILTER EXACT DATE RANGE
    # ==================================================================

    result = result[
        (
            result["TIMESTAMP"] >= start
        )
        &
        (
            result["TIMESTAMP"] <= end
        )
    ].copy()


    # ==================================================================
    # SORT
    # ==================================================================

    result = result.sort_values(
        by=[
            "SYMBOL",
            "TIMESTAMP"
        ]
    ).reset_index(
        drop=True
    )


    return result