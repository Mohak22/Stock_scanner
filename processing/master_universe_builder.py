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
    minimum_price: float = 30.0,
    save_output_flag: bool = True
) -> pd.DataFrame:

    # ==========================================
    # FIND AND SORT FILES BY ACTUAL DATE
    # ==========================================

    file_information = []

    for parquet_file in processed_directory.glob(
        "sec_bhavdata_full_*.parquet"
    ):

        try:

            file_date = pd.to_datetime(

                parquet_file.stem.replace(
                    "sec_bhavdata_full_",
                    ""
                ),

                format="%d%m%Y"

            )

        except ValueError:

            continue

        file_information.append(
            (
                file_date,
                parquet_file
            )
        )

    file_information.sort(
        key=lambda item: item[0],
        reverse=True
    )

    if len(file_information) < liquidity_window:

        raise ValueError(

            f"Only {len(file_information)} processed files found. "
            f"At least {liquidity_window} required."

        )

    # ==========================================
    # KEEP LATEST N TRADING SESSIONS
    # ==========================================

    selected_files = [

        parquet_file

        for _, parquet_file

        in file_information[
            :liquidity_window
        ]

    ]

    # ==========================================
    # LOAD HISTORY
    # ==========================================

    history = pd.concat(

        [

            pd.read_parquet(
                file
            )

            for file in selected_files

        ],

        ignore_index=True

    )

    history["TIMESTAMP"] = pd.to_datetime(
        history["TIMESTAMP"]
    )

    # ==========================================
    # CALCULATE TRADED VALUE
    # ==========================================

    history["TRADED_VALUE"] = (

        history["CLOSE"]
        * history["TOTTRDQTY"]

    )

    # ==========================================
    # CALCULATE AVERAGE TRADED VALUE
    # ==========================================

    liquidity = (

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

    # ==========================================
    # GET LATEST CLOSE FOR EACH STOCK
    # ==========================================

    latest_prices = (

        history

        .sort_values(
            "TIMESTAMP"
        )

        .groupby(
            "SYMBOL",
            as_index=False
        )

        .tail(1)

        [
            [
                "SYMBOL",
                "CLOSE"
            ]
        ]

        .rename(
            columns={
                "CLOSE":
                "LATEST_CLOSE"
            }
        )

    )

    # ==========================================
    # COMBINE ELIGIBILITY INFORMATION
    # ==========================================

    master_universe = liquidity.merge(

        latest_prices,

        on="SYMBOL",

        how="inner"

    )

    # ==========================================
    # LIQUIDITY FILTER
    # ==========================================

    master_universe = master_universe[

        master_universe[
            "AVG_TRADED_VALUE"
        ]
        >= minimum_traded_value

    ]

    # ==========================================
    # PRICE FILTER
    # ==========================================

    master_universe = master_universe[

        master_universe[
            "LATEST_CLOSE"
        ]
        >= minimum_price

    ]

    # ==========================================
    # FINAL UNIVERSE
    # ==========================================

    master_universe = master_universe[
        ["SYMBOL"]
    ]

    master_universe = (

        master_universe

        .sort_values(
            "SYMBOL"
        )

        .reset_index(
            drop=True
        )

    )

    # ==========================================
    # SAVE
    # ==========================================

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