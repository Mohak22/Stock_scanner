# -*- coding: utf-8 -*-
"""
Created on Sun Jul 26 13:22:19 2026

@author: mohak
"""

from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from config.paths import (
    BACKTEST_MARKET_DATA_FOLDER,
    BACKTEST_NIFTY_FILE
)


class NiftyDataRepository:

    TICKER = "^NSEI"

    def __init__(self):

        BACKTEST_MARKET_DATA_FOLDER.mkdir(
            parents=True,
            exist_ok=True
        )

    def load(
        self,
        start_date: date,
        end_date: date
    ) -> pd.DataFrame:

        required_start = pd.Timestamp(
            start_date
        ).normalize()

        required_end = pd.Timestamp(
            end_date
        ).normalize()

        # ==========================================
        # CHECK CACHE
        # ==========================================

        if BACKTEST_NIFTY_FILE.exists():

            cached_df = pd.read_parquet(
                BACKTEST_NIFTY_FILE
            )

            cached_df = self._prepare(
                cached_df
            )

            cached_start = (
                cached_df["Date"].min()
            )

            cached_end = (
                cached_df["Date"].max()
            )

            if (
                cached_start <= required_start
                and
                cached_end >= required_end
            ):

                print(
                    "Using cached NIFTY data."
                )

                return self._filter(

                    nifty_df=cached_df,

                    start_date=required_start,

                    end_date=required_end

                )

        # ==========================================
        # DOWNLOAD REQUIRED NIFTY RANGE
        # ==========================================

        print(
            "Downloading NIFTY historical data..."
        )

        nifty_df = yf.download(

            tickers=self.TICKER,

            start=required_start.date(),

            # yfinance end date is exclusive
            end=(
                required_end.date()
                + timedelta(days=1)
            ),

            progress=False,

            auto_adjust=False

        )

        if nifty_df.empty:

            raise ValueError(
                "NIFTY historical data download returned no data."
            )

        nifty_df = self._prepare(
            nifty_df
        )

        # ==========================================
        # MERGE WITH EXISTING CACHE
        # ==========================================

        if BACKTEST_NIFTY_FILE.exists():

            cached_df = pd.read_parquet(
                BACKTEST_NIFTY_FILE
            )

            cached_df = self._prepare(
                cached_df
            )

            nifty_df = pd.concat(

                [
                    cached_df,
                    nifty_df
                ],

                ignore_index=True

            )

            nifty_df = (

                nifty_df

                .sort_values(
                    "Date"
                )

                .drop_duplicates(
                    subset=["Date"],
                    keep="last"
                )

                .reset_index(
                    drop=True
                )

            )

        # ==========================================
        # SAVE CACHE
        # ==========================================

        nifty_df.to_parquet(

            BACKTEST_NIFTY_FILE,

            index=False

        )

        print(
            f"NIFTY cache updated: "
            f"{BACKTEST_NIFTY_FILE}"
        )

        # ==========================================
        # RETURN REQUESTED RANGE
        # ==========================================

        return self._filter(

            nifty_df=nifty_df,

            start_date=required_start,

            end_date=required_end

        )

    def _prepare(
        self,
        nifty_df: pd.DataFrame
    ) -> pd.DataFrame:

        nifty_df = nifty_df.copy()

        if isinstance(
            nifty_df.columns,
            pd.MultiIndex
        ):

            nifty_df.columns = (
                nifty_df.columns
                .get_level_values(0)
            )

        if "Date" not in nifty_df.columns:

            nifty_df = (
                nifty_df.reset_index()
            )

        if "Date" not in nifty_df.columns:

            raise ValueError(
                "NIFTY data does not contain a Date column."
            )

        nifty_df["Date"] = pd.to_datetime(
            nifty_df["Date"]
        )

        nifty_df["Date"] = (
            nifty_df["Date"]
            .dt.normalize()
        )

        nifty_df = (

            nifty_df

            .sort_values(
                "Date"
            )

            .drop_duplicates(
                subset=["Date"],
                keep="last"
            )

            .reset_index(
                drop=True
            )

        )

        return nifty_df

    def _filter(
        self,
        nifty_df: pd.DataFrame,
        start_date: pd.Timestamp,
        end_date: pd.Timestamp
    ) -> pd.DataFrame:

        filtered_df = nifty_df[

            (
                nifty_df["Date"]
                >= start_date
            )

            &

            (
                nifty_df["Date"]
                <= end_date
            )

        ].copy()

        return filtered_df.reset_index(
            drop=True
        )