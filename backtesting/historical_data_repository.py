# -*- coding: utf-8 -*-
"""
Created on Mon Jul 20 17:44:02 2026

@author: mohak
"""

import pandas as pd

from config.paths import (
    PROCESSED_BHAVCOPY_DIRECTORY,
    RAW_BHAVCOPY_DIRECTORY
)


class HistoricalDataRepository:

    def __init__(self):

        self.data_directory = (
            PROCESSED_BHAVCOPY_DIRECTORY
        )

    def load(
        self,
        start_date,
        end_date,
        history_window: int
    ) -> pd.DataFrame:
        """
        Load bhavcopy data required for an experiment.

        Includes:

        1. Historical trading sessions before the experiment
           for Strategy2 feature calculation.

        2. All trading sessions during the experiment.

        3. All currently available trading sessions after
           experiment end for return analysis.

        StrategyRunner must slice this dataset by
        recommendation date before passing history to
        Strategy2. Therefore future data loaded here must
        never be visible during recommendation generation.
        """

        # =================================================
        # DISCOVER BHAVCOPY FILES
        # =================================================

        parquet_files = sorted(

            self.data_directory.glob(
                "sec_bhavdata_full_*.parquet"
            )

        )

        if not parquet_files:

            raise FileNotFoundError(

                "No processed bhavcopy parquet files found "
                f"in {self.data_directory}"

            )

        file_information = []

        for parquet_file in parquet_files:

            try:

                file_date = pd.to_datetime(

                    parquet_file.stem.replace(
                        "sec_bhavdata_full_",
                        ""
                    ),

                    format="%d%m%Y"

                ).normalize()

            except ValueError:

                continue

            file_information.append(
                (
                    file_date,
                    parquet_file
                )
            )

        if not file_information:

            raise ValueError(
                "No valid bhavcopy files were found."
            )

        file_information.sort(
            key=lambda x: x[0]
        )

        # =================================================
        # EXPERIMENT DATES
        # =================================================

        start_timestamp = pd.Timestamp(
            start_date
        ).normalize()

        end_timestamp = pd.Timestamp(
            end_date
        ).normalize()

        if start_timestamp > end_timestamp:

            raise ValueError(
                "start_date cannot be after end_date."
            )

        # =================================================
        # AVAILABLE TRADING DATES
        # =================================================

        trading_dates = [

            file_date

            for file_date, _

            in file_information

        ]

        # Find first actual trading session
        # on or after experiment start.

        experiment_trading_dates = [

            trading_date

            for trading_date in trading_dates

            if (
                start_timestamp
                <= trading_date
                <= end_timestamp
            )

        ]

        if not experiment_trading_dates:

            raise ValueError(

                "No bhavcopy trading sessions found "
                f"between {start_date} and {end_date}."

            )

        first_experiment_date = (
            experiment_trading_dates[0]
        )

        first_experiment_index = (
            trading_dates.index(
                first_experiment_date
            )
        )

        # =================================================
        # HISTORY START
        # =================================================

        history_start_index = max(

            0,

            first_experiment_index
            - history_window

        )

        history_start_date = (
            trading_dates[
                history_start_index
            ]
        )

        # =================================================
        # SELECT FILES
        #
        # Deliberately no upper experiment-end restriction.
        # Future bhavcopies are required by analysis.
        # =================================================

        selected_files = [

            parquet_file

            for file_date, parquet_file

            in file_information

            if file_date >= history_start_date

        ]

        if not selected_files:

            raise ValueError(
                "No bhavcopy files selected."
            )

        # =================================================
        # LOAD DATA ONCE
        # =================================================

        history = pd.concat(

            (

                pd.read_parquet(
                    parquet_file
                )

                for parquet_file

                in selected_files

            ),

            ignore_index=True

        )

        # =================================================
        # NORMALISE TIMESTAMP
        # =================================================

        history["TIMESTAMP"] = pd.to_datetime(

            history["TIMESTAMP"],

            dayfirst=True,

            errors="coerce"

        )

        history = history.dropna(
            subset=["TIMESTAMP"]
        )

        history["TIMESTAMP"] = (
            history["TIMESTAMP"]
            .dt.normalize()
        )

        # =================================================
        # SORT
        # =================================================

        history.sort_values(

            [
                "SYMBOL",
                "TIMESTAMP"
            ],

            inplace=True

        )

        history.reset_index(

            drop=True,

            inplace=True

        )

        return history
    
    
    def load_market_data(
        self,
        start_date,
        end_date
    ) -> pd.DataFrame:
    
        from config.paths import (
            RAW_BHAVCOPY_DIRECTORY
        )
    
        start_timestamp = pd.Timestamp(
            start_date
        ).normalize()
    
        end_timestamp = pd.Timestamp(
            end_date
        ).normalize()
    
        raw_files = []
    
        for file in RAW_BHAVCOPY_DIRECTORY.glob(
            "sec_bhavdata_full_*.csv"
        ):
    
            try:
    
                file_date = pd.to_datetime(
    
                    file.stem.replace(
                        "sec_bhavdata_full_",
                        ""
                    ),
    
                    format="%d%m%Y"
    
                ).normalize()
    
            except ValueError:
    
                continue
    
            if (
                start_timestamp
                <= file_date
                <= end_timestamp
            ):
    
                raw_files.append(
                    (
                        file_date,
                        file
                    )
                )
    
        raw_files.sort(
            key=lambda item: item[0]
        )
    
        if not raw_files:
    
            raise ValueError(
    
                "No raw bhavcopy files found between "
                f"{start_date} and {end_date}."
    
            )
    
        market_data = pd.concat(
    
            [
    
                pd.read_csv(
                    file
                )
    
                for _, file in raw_files
    
            ],
    
            ignore_index=True
    
        )
    
        # ==========================================
        # CLEAN RAW NSE DATA
        # ==========================================
        
        # Remove whitespace from column names
        market_data.columns = (
            market_data.columns
            .str.strip()
        )
        
        # Remove whitespace from all text columns
        object_columns = (
            market_data
            .select_dtypes(
                include=["object"]
            )
            .columns
        )
        
        for column in object_columns:
        
            market_data[column] = (
                market_data[column]
                .astype(str)
                .str.strip()
            )
    
        # Keep normal equity series only
        market_data = market_data[
            market_data["SERIES"] == "EQ"
        ].copy()
    
        # Standardise columns for generic return calculator
        market_data = market_data.rename(
            columns={
                "DATE1": "TIMESTAMP",
                "OPEN_PRICE": "OPEN",
                "HIGH_PRICE": "HIGH",
                "LOW_PRICE": "LOW",
                "CLOSE_PRICE": "CLOSE"
            }
        )
    
        market_data["TIMESTAMP"] = pd.to_datetime(
    
            market_data["TIMESTAMP"],
    
            format="%d-%b-%Y",
    
            errors="coerce"
    
        )
    
        market_data = market_data.dropna(
            subset=["TIMESTAMP"]
        )
    
        market_data["TIMESTAMP"] = (
            market_data["TIMESTAMP"]
            .dt.normalize()
        )
    
        market_data = market_data.sort_values(
            [
                "SYMBOL",
                "TIMESTAMP"
            ]
        )
    
        market_data = market_data.reset_index(
            drop=True
        )
    
        return market_data