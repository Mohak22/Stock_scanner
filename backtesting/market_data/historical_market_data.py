# -*- coding: utf-8 -*-
"""
Created on Mon Aug 10 15:14:57 2026

@author: mohak
"""

"""
Historical Market Data Collector

Responsibilities:
    - Load the current master universe.
    - Maintain one Parquet file per stock.
    - Fetch historical OHLCV data from Yahoo Finance.
    - Maintain data from START_DATE through data_as_of.
    - Incrementally download only missing data.
    - Never retain observations after data_as_of.

Important:
    data_as_of is supplied by the Daily Data Preparation pipeline.

    The caller is responsible for deciding the cutoff.

    This module NEVER uses today's date as the data cutoff.
"""


from pathlib import Path
from datetime import date, timedelta
import time

import pandas as pd
import yfinance as yf

from config.paths import (
    DATA_REPOSITORY,
    MASTER_UNIVERSE_FILE,
    HISTORICAL_MARKET_DATA_RAW_FOLDER,
    HISTORICAL_MARKET_DATA_LOGS_FOLDER,
    HISTORICAL_MARKET_DATA_SUCCESS_LOG_FILE,
    HISTORICAL_MARKET_DATA_FAILURE_LOG_FILE
)

# ============================================================
# CONFIGURATION
# ============================================================

# Historical data will be maintained from this date onward.
START_DATE = "2016-01-01"

# NSE Yahoo Finance suffix.
EXCHANGE_SUFFIX = ".NS"


# ------------------------------------------------------------
# Repository / data paths
# ------------------------------------------------------------

DATA_ROOT = DATA_REPOSITORY

MASTER_UNIVERSE_FILE = MASTER_UNIVERSE_FILE

OUTPUT_DIRECTORY = (
    HISTORICAL_MARKET_DATA_RAW_FOLDER
)

LOG_DIRECTORY = (
    HISTORICAL_MARKET_DATA_LOGS_FOLDER
)

SUCCESS_LOG_FILE = (
    HISTORICAL_MARKET_DATA_SUCCESS_LOG_FILE
)

FAILURE_LOG_FILE = (
    HISTORICAL_MARKET_DATA_FAILURE_LOG_FILE
)


# Number of retries for a failed yfinance request.
MAX_RETRIES = 3


# Small pause between requests.
REQUEST_DELAY_SECONDS = 0.5


# ============================================================
# DIRECTORY SETUP
# ============================================================

OUTPUT_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)


LOG_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# LOAD MASTER UNIVERSE
# ============================================================

def load_master_universe(
    file_path: Path
) -> list[str]:

    """
    Load the current master universe.

    The universe is intentionally read fresh on every run.

    Therefore, if the number of stocks changes,
    this collector automatically follows the
    latest universe.
    """

    if not file_path.exists():

        raise FileNotFoundError(
            f"Master universe not found:\n"
            f"{file_path}"
        )


    universe = pd.read_csv(
        file_path
    )


    if "SYMBOL" not in universe.columns:

        raise ValueError(
            "master_universe.csv must contain "
            "a 'SYMBOL' column."
        )


    symbols = (
        universe["SYMBOL"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .drop_duplicates()
        .tolist()
    )


    return symbols


# ============================================================
# READ EXISTING STOCK FILE
# ============================================================

def load_existing_data(
    file_path: Path
) -> pd.DataFrame:

    """
    Load an existing stock Parquet file.

    Returns an empty DataFrame if the file does not exist
    or cannot be read.
    """

    if not file_path.exists():

        return pd.DataFrame()


    try:

        data = pd.read_parquet(
            file_path
        )


        if data.empty:

            return pd.DataFrame()


        if "Date" not in data.columns:

            raise ValueError(
                "Existing stock file does not contain "
                "'Date' column."
            )


        data["Date"] = pd.to_datetime(
            data["Date"]
        )


        # --------------------------------------------------------
        # Remove timezone if present.
        # --------------------------------------------------------

        if data["Date"].dt.tz is not None:

            data["Date"] = (
                data["Date"]
                .dt.tz_localize(None)
            )


        data = (
            data
            .sort_values("Date")
            .reset_index(drop=True)
        )


        return data


    except Exception as error:

        print(
            f"Could not read existing file "
            f"{file_path.name}: {error}"
        )


        return pd.DataFrame()


# ============================================================
# FETCH FROM YFINANCE
# ============================================================

def fetch_stock_data(
    symbol: str,
    start_date: str,
    end_date: str
) -> pd.DataFrame:

    """
    Fetch historical OHLCV data from Yahoo Finance.

    IMPORTANT:

    end_date is exclusive in yfinance.

    Therefore, if we want data through:

        2026-08-16

    we request:

        2026-08-17

    This allows the final available trading observation
    to be 2026-08-14 when 15th/16th are non-trading days.
    """

    ticker_symbol = (
        f"{symbol}{EXCHANGE_SUFFIX}"
    )


    for attempt in range(
        1,
        MAX_RETRIES + 1
    ):

        try:

            print(
                f"  Fetching {ticker_symbol}: "
                f"{start_date} -> {end_date} "
                f"(attempt {attempt})"
            )


            data = yf.download(

                ticker_symbol,

                start=start_date,

                end=end_date,

                auto_adjust=False,

                actions=True,

                progress=False,

                threads=False

            )


            if data.empty:

                print(
                    f"  No data returned for "
                    f"{ticker_symbol}"
                )

                return pd.DataFrame()


            # ----------------------------------------------------
            # yfinance can sometimes return MultiIndex columns.
            # ----------------------------------------------------

            if isinstance(
                data.columns,
                pd.MultiIndex
            ):

                data.columns = [

                    column[0]

                    for column in data.columns

                ]


            data = data.reset_index()


            # ----------------------------------------------------
            # Required columns
            # ----------------------------------------------------

            required_columns = [

                "Date",
                "Open",
                "High",
                "Low",
                "Close",
                "Adj Close",
                "Volume"

            ]


            missing_columns = [

                column

                for column in required_columns

                if column not in data.columns

            ]


            if missing_columns:

                raise ValueError(

                    f"Missing columns for "
                    f"{ticker_symbol}: "
                    f"{missing_columns}"

                )


            data = data[
                required_columns
            ].copy()


            # ----------------------------------------------------
            # Clean dates
            # ----------------------------------------------------

            data["Date"] = pd.to_datetime(
                data["Date"]
            )


            if data["Date"].dt.tz is not None:

                data["Date"] = (
                    data["Date"]
                    .dt.tz_localize(None)
                )


            # ----------------------------------------------------
            # Remove completely invalid price rows.
            # ----------------------------------------------------

            data = data.dropna(
                subset=[
                    "Open",
                    "High",
                    "Low",
                    "Close"
                ]
            )


            # ----------------------------------------------------
            # Sort
            # ----------------------------------------------------

            data = (
                data
                .sort_values("Date")
                .reset_index(drop=True)
            )


            return data


        except Exception as error:

            print(
                f"  Error fetching "
                f"{ticker_symbol}: {error}"
            )


            if attempt < MAX_RETRIES:

                time.sleep(
                    2
                )


    return pd.DataFrame()


# ============================================================
# MERGE EXISTING + NEW DATA
# ============================================================

def merge_stock_data(
    existing_data: pd.DataFrame,
    new_data: pd.DataFrame
) -> pd.DataFrame:

    """
    Merge existing and newly downloaded observations.

    Duplicate dates are removed.

    The newly downloaded observation is kept if
    a duplicate date exists.
    """

    if existing_data.empty:

        combined = new_data.copy()


    elif new_data.empty:

        combined = existing_data.copy()


    else:

        combined = pd.concat(
            [
                existing_data,
                new_data
            ],
            ignore_index=True
        )


    if combined.empty:

        return combined


    combined["Date"] = pd.to_datetime(
        combined["Date"]
    )


    if combined["Date"].dt.tz is not None:

        combined["Date"] = (
            combined["Date"]
            .dt.tz_localize(None)
        )


    combined = (
        combined
        .drop_duplicates(
            subset=["Date"],
            keep="last"
        )
        .sort_values("Date")
        .reset_index(drop=True)
    )


    return combined


# ============================================================
# PROCESS ONE STOCK
# ============================================================

def process_stock(
    symbol: str,
    data_as_of: date
) -> dict:

    """
    Maintain the historical file for one stock.

    Data is maintained from:

        START_DATE

    through:

        data_as_of

    Logic:

    1. File does not exist:
       fetch START_DATE -> data_as_of.

    2. File exists:
       remove any observations after data_as_of.

    3. Find latest valid stored date.

    4. Fetch only the missing range.

    5. Merge and save.

    No current system date is used.
    """

    output_file = (
        OUTPUT_DIRECTORY
        / f"{symbol}.parquet"
    )


    # --------------------------------------------------------
    # Load existing data
    # --------------------------------------------------------

    existing_data = load_existing_data(
        output_file
    )


    # --------------------------------------------------------
    # Convert cutoff to Timestamp
    # --------------------------------------------------------

    cutoff_date = pd.Timestamp(
        data_as_of
    )


    # --------------------------------------------------------
    # SAFETY:
    # Remove any existing observations after cutoff.
    #
    # This is important if an earlier run accidentally fetched
    # today's data.
    # --------------------------------------------------------

    if not existing_data.empty:

        existing_data = existing_data[
            existing_data["Date"]
            <= cutoff_date
        ].copy()


        existing_data = (
            existing_data
            .sort_values("Date")
            .reset_index(drop=True)
        )


    # --------------------------------------------------------
    # Determine fetch start
    # --------------------------------------------------------

    if existing_data.empty:

        fetch_start = pd.Timestamp(
            START_DATE
        )

        previous_last_date = None


    else:

        previous_last_date = (
            existing_data["Date"].max()
        )


        fetch_start = (
            previous_last_date
            + pd.Timedelta(days=1)
        )


    # --------------------------------------------------------
    # Already completely up to date
    # --------------------------------------------------------

    if fetch_start > cutoff_date:

        # ----------------------------------------------------
        # Save again if the existing file was modified by the
        # cutoff cleanup.
        # ----------------------------------------------------

        if output_file.exists():

            existing_data.to_parquet(
                output_file,
                index=False
            )


        return {

            "symbol": symbol,

            "status": "up_to_date",

            "rows_before": len(
                existing_data
            ),

            "rows_added": 0,

            "rows_after": len(
                existing_data
            ),

            "first_date": (

                str(
                    existing_data[
                        "Date"
                    ].min().date()
                )

                if not existing_data.empty

                else None

            ),

            "last_date": (

                str(
                    existing_data[
                        "Date"
                    ].max().date()
                )

                if not existing_data.empty

                else None

            )

        }


    # --------------------------------------------------------
    # yfinance end date is exclusive.
    #
    # Therefore:
    #
    # desired final date = data_as_of
    #
    # API end date = data_as_of + 1 day
    # --------------------------------------------------------

    fetch_end = (
        cutoff_date
        + pd.Timedelta(days=1)
    )


    # --------------------------------------------------------
    # Fetch missing range
    # --------------------------------------------------------

    new_data = fetch_stock_data(

        symbol=symbol,

        start_date=fetch_start.strftime(
            "%Y-%m-%d"
        ),

        end_date=fetch_end.strftime(
            "%Y-%m-%d"
        )

    )


    # --------------------------------------------------------
    # SAFETY:
    # Even if Yahoo somehow returns a row after the cutoff,
    # remove it before saving.
    # --------------------------------------------------------

    if not new_data.empty:

        new_data = new_data[
            new_data["Date"]
            <= cutoff_date
        ].copy()


        new_data = (
            new_data
            .sort_values("Date")
            .reset_index(drop=True)
        )


    # --------------------------------------------------------
    # Fetch failed / no new data
    # --------------------------------------------------------

    if new_data.empty:

        if existing_data.empty:

            return {

                "symbol": symbol,

                "status": "failed",

                "rows_before": 0,

                "rows_added": 0,

                "rows_after": 0,

                "first_date": None,

                "last_date": None

            }


        # ----------------------------------------------------
        # Save cleaned existing data.
        # ----------------------------------------------------

        existing_data.to_parquet(
            output_file,
            index=False
        )


        return {

            "symbol": symbol,

            "status": "no_new_data",

            "rows_before": len(
                existing_data
            ),

            "rows_added": 0,

            "rows_after": len(
                existing_data
            ),

            "first_date": str(
                existing_data[
                    "Date"
                ].min().date()
            ),

            "last_date": str(
                existing_data[
                    "Date"
                ].max().date()
            )

        }


    # --------------------------------------------------------
    # Merge
    # --------------------------------------------------------

    rows_before = len(
        existing_data
    )


    combined = merge_stock_data(

        existing_data=existing_data,

        new_data=new_data

    )


    # --------------------------------------------------------
    # FINAL CUTOFF SAFETY
    # --------------------------------------------------------

    combined = combined[
        combined["Date"]
        <= cutoff_date
    ].copy()


    combined = (
        combined
        .sort_values("Date")
        .reset_index(drop=True)
    )


    rows_after = len(
        combined
    )


    rows_added = (
        rows_after
        - rows_before
    )


    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    combined.to_parquet(

        output_file,

        index=False

    )


    return {

        "symbol": symbol,

        "status": "success",

        "rows_before": rows_before,

        "rows_added": rows_added,

        "rows_after": rows_after,

        "first_date": str(
            combined[
                "Date"
            ].min().date()
        ),

        "last_date": str(
            combined[
                "Date"
            ].max().date()
        )

    }


# ============================================================
# LOG RESULT
# ============================================================

def log_result(
    result: dict
) -> None:

    """
    Append the result to the appropriate log file.
    """

    if result["status"] == "failed":

        log_file = (
            FAILURE_LOG_FILE
        )

    else:

        log_file = (
            SUCCESS_LOG_FILE
        )


    log_row = pd.DataFrame(
        [result]
    )


    if log_file.exists():

        log_row.to_csv(

            log_file,

            mode="a",

            header=False,

            index=False

        )

    else:

        log_row.to_csv(

            log_file,

            mode="w",

            header=True,

            index=False

        )


# ============================================================
# MAIN
# ============================================================

def main(
    data_as_of: date
):

    """
    Main historical market data collector.

    data_as_of is supplied by the Daily Data Preparation
    pipeline.

    Example:

        data_as_of = 2026-08-16

    The collector will maintain data only through that date.
    """

    print(
        "\n"
        "==================================================\n"
        " HISTORICAL MARKET DATA COLLECTOR\n"
        "=================================================="
    )


    print(
        f"\nData cutoff:\n"
        f"{data_as_of}"
    )


    print(
        f"\nMaster Universe:\n"
        f"{MASTER_UNIVERSE_FILE}"
    )


    print(
        f"\nOutput Directory:\n"
        f"{OUTPUT_DIRECTORY}"
    )


    print(
        f"\nHistorical Start Date:\n"
        f"{START_DATE}"
    )


    # --------------------------------------------------------
    # Validate cutoff
    # --------------------------------------------------------

    if not isinstance(
        data_as_of,
        date
    ):

        raise TypeError(
            "data_as_of must be a datetime.date object."
        )


    # --------------------------------------------------------
    # Validate master universe
    # --------------------------------------------------------

    symbols = load_master_universe(
        MASTER_UNIVERSE_FILE
    )


    print(
        f"\nStocks in current universe: "
        f"{len(symbols)}"
    )


    # --------------------------------------------------------
    # Process stocks one by one
    # --------------------------------------------------------

    successful = 0

    failed = 0

    up_to_date = 0

    no_new_data = 0


    for index, symbol in enumerate(

        symbols,

        start=1

    ):

        print(
            "\n"
            "--------------------------------------------------"
        )


        print(
            f"[{index}/{len(symbols)}] "
            f"{symbol}"
        )


        try:

            result = process_stock(

                symbol=symbol,

                data_as_of=data_as_of

            )


            log_result(
                result
            )


            status = result[
                "status"
            ]


            print(
                f"  Status       : "
                f"{status}"
            )


            print(
                f"  Rows before  : "
                f"{result['rows_before']}"
            )


            print(
                f"  Rows added   : "
                f"{result['rows_added']}"
            )


            print(
                f"  Rows after   : "
                f"{result['rows_after']}"
            )


            print(
                f"  First date   : "
                f"{result['first_date']}"
            )


            print(
                f"  Last date    : "
                f"{result['last_date']}"
            )


            if status == "success":

                successful += 1


            elif status == "failed":

                failed += 1


            elif status == "up_to_date":

                up_to_date += 1


            elif status == "no_new_data":

                no_new_data += 1


        except Exception as error:

            failed += 1


            result = {

                "symbol": symbol,

                "status": "failed",

                "rows_before": 0,

                "rows_added": 0,

                "rows_after": 0,

                "first_date": None,

                "last_date": None,

                "error": str(error)

            }


            log_result(
                result
            )


            print(
                f"  UNEXPECTED ERROR: "
                f"{error}"
            )


        # ----------------------------------------------------
        # Small delay between requests.
        # ----------------------------------------------------

        time.sleep(
            REQUEST_DELAY_SECONDS
        )


    # --------------------------------------------------------
    # Final summary
    # --------------------------------------------------------

    print(
        "\n"
        "==================================================\n"
        " COLLECTION COMPLETE\n"
        "=================================================="
    )


    print(
        f"\nData cutoff : "
        f"{data_as_of}"
    )


    print(
        f"\nTotal stocks : "
        f"{len(symbols)}"
    )


    print(
        f"Successful   : "
        f"{successful}"
    )


    print(
        f"Up to date   : "
        f"{up_to_date}"
    )


    print(
        f"No new data  : "
        f"{no_new_data}"
    )


    print(
        f"Failed       : "
        f"{failed}"
    )


    print(
        f"\nData stored in:\n"
        f"{OUTPUT_DIRECTORY}"
    )


    print(
        f"\nFailure log:\n"
        f"{FAILURE_LOG_FILE}"
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # Standalone execution
    #
    # IMPORTANT:
    # Standalone execution also uses YESTERDAY.
    # --------------------------------------------------------

    standalone_data_as_of = (
        date.today()
        - timedelta(days=1)
    )


    main(
        data_as_of=standalone_data_as_of
    )