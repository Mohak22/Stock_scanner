# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 11:41:09 2026

@author: mohak
"""

from pathlib import Path

import pandas as pd

from reports.excel_report_generator import (
    save_output
)

def build_master_universe(
    processed_directory: Path,
    liquidity_window: int = 20,
    minimum_traded_value: float = 1_00_00_000,
    save_output_flag: bool = True
) -> pd.DataFrame:

    parquet_files = sorted(
        processed_directory.glob("*.parquet"),
        reverse=True
    )

    if len(parquet_files) < liquidity_window:

        raise ValueError(
            f"Only {len(parquet_files)} processed files found. "
            f"At least {liquidity_window} required."
        )

    parquet_files = parquet_files[:liquidity_window]

    history = pd.concat(
        [
            pd.read_parquet(file)
            for file in parquet_files
        ],
        ignore_index=True
    )

    history["TRADED_VALUE"] = (
        history["CLOSE"]
        * history["TOTTRDQTY"]
    )

    master_universe = (

        history

        .groupby(
            "SYMBOL",
            as_index=False
        )["TRADED_VALUE"]

        .mean()

        .rename(
            columns={
                "TRADED_VALUE":
                "AVG_TRADED_VALUE"
            }
        )

    )

    master_universe = master_universe[
        master_universe["AVG_TRADED_VALUE"]
        >= minimum_traded_value
    ]

    master_universe = master_universe[
        ["SYMBOL"]
    ]

    master_universe = (
        master_universe
        .sort_values("SYMBOL")
        .reset_index(drop=True)
    )

    save_output(
        dataframe=master_universe,
        folder_name="",
        file_name="master_universe.csv",
        save_output=save_output_flag
    )

    print(
        f"\nMaster Universe Created : "
        f"{len(master_universe)} Stocks"
    )

    return master_universe