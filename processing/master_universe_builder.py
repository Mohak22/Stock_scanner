# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 11:41:09 2026

@author: mohak
"""

"""
Created on Mon Jul 6 11:41:09 2026

Master Universe Builder

Responsibilities:
    - Identify the latest available trading sessions.
    - Calculate average traded value over the latest
      liquidity window.
    - Apply minimum liquidity and price filters.
    - Build the current research/production universe.
    - Save master_universe.csv.

IMPORTANT:

This function does NOT build the complete historical research dataset.

The complete historical dataset remains stored separately
in processed Bhavcopy Parquet files.

The master universe is only the CURRENT eligible universe.
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

    print(
        "\n"
        + "=" * 70
    )

    print(
        "BUILDING MASTER UNIVERSE"
    )

    print(
        "=" * 70
    )


    # ==================================================================
    # FIND PROCESSED BHAVCOPY FILES
    # ==================================================================

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


    # ==================================================================
    # SORT BY ACTUAL TRADING DATE
    # ==================================================================

    file_information.sort(
        key=lambda item: item[0],
        reverse=True
    )


    # ==================================================================
    # VALIDATE HISTORY
    # ==================================================================

    if len(file_information) < liquidity_window:

        raise ValueError(

            f"Only {len(file_information)} processed "
            f"Bhavcopy files found. "

            f"At least {liquidity_window} "
            f"trading sessions are required."

        )


    # ==================================================================
    # SELECT LATEST N TRADING SESSIONS
    # ==================================================================

    selected_files = [

        parquet_file

        for _, parquet_file

        in file_information[
            :liquidity_window
        ]

    ]


    print(
        f"\nLiquidity window : "
        f"{liquidity_window} trading sessions"
    )

    print(
        f"Latest session   : "
        f"{file_information[0][0].date()}"
    )

    print(
        f"Oldest session   : "
        f"{file_information[liquidity_window - 1][0].date()}"
    )


    # ==================================================================
    # LOAD ONLY REQUIRED HISTORY
    # ==================================================================

    history = pd.concat(

        [

            pd.read_parquet(
                file
            )

            for file in selected_files

        ],

        ignore_index=True

    )


    # ==================================================================
    # NORMALIZE TIMESTAMP
    # ==================================================================

    history["TIMESTAMP"] = pd.to_datetime(
        history["TIMESTAMP"],
        errors="coerce"
    )


    # ==================================================================
    # CALCULATE TRADED VALUE
    # ==================================================================

    history["TRADED_VALUE"] = (

        history["CLOSE"]

        *

        history["TOTTRDQTY"]

    )


    # ==================================================================
    # AVERAGE TRADED VALUE
    # ==================================================================

    liquidity = (

        history

        .groupby(
            "SYMBOL",
            as_index=False
        )

        ["TRADED_VALUE"]

        .mean()

        .rename(
            columns={
                "TRADED_VALUE":
                "AVG_TRADED_VALUE"
            }
        )

    )


    # ==================================================================
    # LATEST CLOSE
    # ==================================================================

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


    # ==================================================================
    # COMBINE LIQUIDITY + PRICE
    # ==================================================================

    master_universe = liquidity.merge(

        latest_prices,

        on="SYMBOL",

        how="inner"

    )


    # ==================================================================
    # LIQUIDITY FILTER
    # ==================================================================

    master_universe = master_universe[

        master_universe[
            "AVG_TRADED_VALUE"
        ]

        >=

        minimum_traded_value

    ]


    # ==================================================================
    # PRICE FILTER
    # ==================================================================

    master_universe = master_universe[

        master_universe[
            "LATEST_CLOSE"
        ]

        >=

        minimum_price

    ]


    # ==================================================================
    # KEEP SYMBOL ONLY
    # ==================================================================

    master_universe = master_universe[
        ["SYMBOL"]
    ]


    # ==================================================================
    # SORT
    # ==================================================================

    master_universe = (

        master_universe

        .drop_duplicates(
            subset=["SYMBOL"]
        )

        .sort_values(
            "SYMBOL"
        )

        .reset_index(
            drop=True
        )

    )


    # ==================================================================
    # SAVE
    # ==================================================================

    save_output(

        dataframe=master_universe,

        folder_name="",

        file_name="master_universe.csv",

        save_output=save_output_flag

    )


    # ==================================================================
    # SUMMARY
    # ==================================================================

    print(
        "\n"
        + "-" * 70
    )

    print(
        "MASTER UNIVERSE CREATED"
    )

    print(
        "-" * 70
    )

    print(
        f"Eligible stocks : "
        f"{len(master_universe)}"
    )

    print(
        f"Minimum traded value : "
        f"₹{minimum_traded_value:,.0f}"
    )

    print(
        f"Minimum price : "
        f"₹{minimum_price:,.2f}"
    )

    print(
        f"Liquidity window : "
        f"{liquidity_window} trading sessions"
    )


    return master_universe