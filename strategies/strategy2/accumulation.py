# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 16:11:47 2026

@author: mohak
"""
# -*- coding: utf-8 -*-
"""
Strategy 2 - Accumulation Strategy

Responsibilities:
    - Load historical processed Bhavcopy data.
    - Load corresponding RAW NSE MTO / delivery files directly.
    - Merge delivery information into Bhavcopy history.
    - Calculate moving averages.
    - Calculate RSI.
    - Calculate delivery features.
    - Calculate volume features.
    - Calculate strategy score.
    - Rank recommendations.

Production data source:

    STOCK_SCANNER_DATA/
        processed/
            bhavcopy/

        raw/
            nse/
                mto/
                    MTO_DDMMYYYY.DAT

IMPORTANT:
    MTO files are intentionally read directly from RAW storage.

    We do NOT create or depend on:

        processed/mto/

This module does NOT:
    - Download NSE data.
    - Download MTO data.
    - Modify raw files.
    - Run data synchronization.
"""


from datetime import date, datetime

import pandas as pd
import numpy as np


from config.paths import (
    PROCESSED_BHAVCOPY_DIRECTORY,
    RAW_NSE_DIRECTORY,
    MASTER_UNIVERSE_FILE
)


from indicators.ema_engine import (
    calculate_ema
)


from strategies.strategy2.strategy2_config import (
    Strategy2Config
)


class Strategy2:

    def __init__(
        self,
        config: Strategy2Config
    ):

        self.config = config


    # ==================================================================
    # RUN
    # ==================================================================

    def run(
        self,
        recommendation_date: date,
        history: pd.DataFrame | None = None
    ) -> pd.DataFrame:

        """
        Generate recommendations for a given recommendation date.

        Production:
            history=None

        Backtesting:
            Supply preloaded history to avoid repeated disk I/O.
        """

        # --------------------------------------------------------------
        # PRODUCTION: LOAD HISTORY
        # --------------------------------------------------------------

        if history is None:

            history = self._load_history(
                recommendation_date
            )


        # --------------------------------------------------------------
        # COPY
        # --------------------------------------------------------------

        history = history.copy()


        # --------------------------------------------------------------
        # FEATURE ENGINEERING
        # --------------------------------------------------------------

        history = self._build_features(
            history
        )


        # --------------------------------------------------------------
        # KEEP LATEST TRADING DAY
        # --------------------------------------------------------------

        history = self._keep_latest_trading_day(
            history
        )


        # --------------------------------------------------------------
        # SCORE
        # --------------------------------------------------------------

        history = self._calculate_delivery_score(
            history
        )


        history = self._calculate_volume_score(
            history
        )


        history = self._calculate_final_score(
            history
        )


        # --------------------------------------------------------------
        # REMOVE INVALID SCORES
        # --------------------------------------------------------------

        history = history.dropna(
            subset=["FINAL_SCORE"]
        )


        # --------------------------------------------------------------
        # RANK
        # --------------------------------------------------------------

        history = self._rank_recommendations(
            history
        )


        return history


    # ==================================================================
    # BUILD FEATURES
    # ==================================================================

    def _build_features(
        self,
        history: pd.DataFrame
    ) -> pd.DataFrame:

        history = self._add_moving_averages(
            history
        )


        history = self._classify_direction(
            history
        )


        history = self._add_rsi(
            history
        )


        history = self._add_delivery_features(
            history
        )


        history = self._add_volume_features(
            history
        )


        history = history.replace(

            [np.inf, -np.inf],

            np.nan

        )


        return history


    # ==================================================================
    # LOAD BHAVCOPY HISTORY
    # ==================================================================

    def _load_history(
        self,
        recommendation_date: date
    ) -> pd.DataFrame:

        """
        Load processed Bhavcopy history.

        Then merge RAW MTO delivery data.

        Only Bhavcopy files <= recommendation_date are considered.

        The latest `history_window` Bhavcopy sessions are loaded.
        """

        # ==============================================================
        # FIND BHAVCOPY FILES
        # ==============================================================

        parquet_files = []


        for file in PROCESSED_BHAVCOPY_DIRECTORY.glob(
            "*.parquet"
        ):

            try:

                file_date = date.fromisoformat(

                    f"{file.stem[-4:]}"

                    f"-{file.stem[-6:-4]}"

                    f"-{file.stem[-8:-6]}"

                )

            except ValueError:

                continue


            if file_date <= recommendation_date:

                parquet_files.append(

                    (
                        file_date,
                        file
                    )

                )


        # ==============================================================
        # SELECT LATEST HISTORY WINDOW
        # ==============================================================

        parquet_files = [

            file

            for _, file in sorted(

                parquet_files,

                key=lambda x: x[0],

                reverse=True

            )[

                :self.config.history_window

            ]

        ]


        if not parquet_files:

            raise ValueError(

                "No processed Bhavcopy files found "

                f"up to {recommendation_date}."

            )


        # ==============================================================
        # LOAD BHAVCOPY
        # ==============================================================

        history = pd.concat(

            [

                pd.read_parquet(
                    file
                )

                for file in parquet_files

            ],

            ignore_index=True

        )


        # ==============================================================
        # NORMALIZE BHAVCOPY DATE
        # ==============================================================

        history["TIMESTAMP"] = pd.to_datetime(

            history["TIMESTAMP"],

            errors="coerce"

        ).dt.date


        # ==============================================================
        # NORMALIZE SYMBOL
        # ==============================================================

        history["SYMBOL"] = (

            history["SYMBOL"]

            .astype(str)

            .str.strip()

            .str.upper()

        )


        # ==============================================================
        # MASTER UNIVERSE FILTER
        # ==============================================================

        master_universe = pd.read_csv(

            MASTER_UNIVERSE_FILE

        )


        master_universe["SYMBOL"] = (

            master_universe["SYMBOL"]

            .astype(str)

            .str.strip()

            .str.upper()

        )


        history = history[

            history["SYMBOL"].isin(

                master_universe["SYMBOL"]

            )

        ]


        # ==============================================================
        # LOAD RAW MTO
        # ==============================================================

        history = self._merge_mto_history(

            history

        )


        # ==============================================================
        # SORT
        # ==============================================================

        history = history.sort_values(

            by=[

                "SYMBOL",

                "TIMESTAMP"

            ]

        ).reset_index(

            drop=True

        )


        return history


    # ==================================================================
    # MERGE RAW MTO HISTORY
    # ==================================================================

    def _merge_mto_history(
        self,
        history: pd.DataFrame
    ) -> pd.DataFrame:

        """
        Read RAW NSE MTO files directly.

        Expected location:

            STOCK_SCANNER_DATA/
                raw/
                    nse/
                        mto/

        Expected MTO record format:

            20,Serial No,Symbol,Series,
            Quantity Traded,Deliverable Quantity,
            Deliverable Percentage

        Example:

            20,123,20MICRONS,EQ,253140,123456,48.77

        Only EQ records are retained.

        MTO is merged using:

            SYMBOL + TIMESTAMP
        """

        # ==============================================================
        # REQUIRED BHAVCOPY COLUMNS
        # ==============================================================

        required_bhavcopy = [

            "SYMBOL",
            "TIMESTAMP"

        ]


        missing = [

            column

            for column in required_bhavcopy

            if column not in history.columns

        ]


        if missing:

            raise ValueError(

                "Missing Bhavcopy columns: "

                f"{missing}"

            )


        # ==============================================================
        # NORMALIZE BHAVCOPY
        # ==============================================================

        history["SYMBOL"] = (

            history["SYMBOL"]

            .astype(str)

            .str.strip()

            .str.upper()

        )


        history["TIMESTAMP"] = pd.to_datetime(

            history["TIMESTAMP"],

            errors="coerce"

        ).dt.date


        # ==============================================================
        # DATE RANGE
        # ==============================================================

        min_date = history["TIMESTAMP"].min()

        max_date = history["TIMESTAMP"].max()


        if pd.isna(min_date) or pd.isna(max_date):

            raise ValueError(

                "Bhavcopy history contains no valid "

                "TIMESTAMP values."

            )


        print(

            "\nReading RAW MTO files directly:"

        )

        print(

            f"  Date range : "

            f"{min_date} -> {max_date}"

        )


        # ==============================================================
        # RAW MTO DIRECTORY
        # ==============================================================

        raw_mto_directory = (

            RAW_NSE_DIRECTORY

            / "mto"

        )


        if not raw_mto_directory.exists():

            raise FileNotFoundError(

                "RAW MTO directory does not exist: "

                f"{raw_mto_directory}"

            )


        # ==============================================================
        # FIND RELEVANT MTO FILES
        # ==============================================================

        mto_files = []


        for file in raw_mto_directory.glob(

            "MTO_*.DAT"

        ):

            try:

                filename_date = file.stem[4:]


                file_date = datetime.strptime(

                    filename_date,

                    "%d%m%Y"

                ).date()


            except (

                ValueError,

                TypeError

            ):

                continue


            if (

                min_date

                <= file_date

                <= max_date

            ):

                mto_files.append(

                    (

                        file_date,

                        file

                    )

                )


        # ==============================================================
        # SORT CHRONOLOGICALLY
        # ==============================================================

        mto_files.sort(

            key=lambda item: item[0]

        )


        # ==============================================================
        # SAFETY CHECK
        # ==============================================================

        if not mto_files:

            raise ValueError(

                "No RAW MTO files found for "

                f"Bhavcopy range "

                f"{min_date} -> {max_date}."

            )


        print(

            f"  RAW MTO files : "

            f"{len(mto_files)}"

        )


        # ==============================================================
        # LOAD RAW MTO FILES
        # ==============================================================

        mto_frames = []


        for file_date, file in mto_files:

            rows = []


            try:

                with open(

                    file,

                    "r",

                    encoding="utf-8",

                    errors="replace"

                ) as source:

                    lines = source.readlines()


            except OSError as error:

                raise OSError(

                    "Unable to read MTO file: "

                    f"{file}"

                ) from error


            # ==========================================================
            # PARSE RECORDS
            # ==========================================================

            for line in lines:

                line = line.strip()


                if not line:

                    continue


                parts = line.split(",")


                # ------------------------------------------------------
                # Valid MTO data record:
                #
                # 20,SR_NO,SYMBOL,SERIES,QTY,DELIV_QTY,DELIV_PER
                # ------------------------------------------------------

                if len(parts) < 7:

                    continue


                # ------------------------------------------------------
                # Record type 20 = security record
                # ------------------------------------------------------

                if parts[0].strip() != "20":

                    continue


                symbol = (

                    parts[2]

                    .strip()

                    .upper()

                )


                series = (

                    parts[3]

                    .strip()

                    .upper()

                )


                # ------------------------------------------------------
                # Keep only equity series
                # ------------------------------------------------------

                if series != "EQ":

                    continue


                # ------------------------------------------------------
                # Quantity traded
                # ------------------------------------------------------

                try:

                    qty_traded = int(

                        float(

                            parts[4].strip()

                        )

                    )

                except (

                    ValueError,

                    TypeError

                ):

                    continue


                # ------------------------------------------------------
                # Deliverable quantity
                # ------------------------------------------------------

                try:

                    deliv_qty = int(

                        float(

                            parts[5].strip()

                        )

                    )

                except (

                    ValueError,

                    TypeError

                ):

                    continue


                # ------------------------------------------------------
                # Delivery percentage
                # ------------------------------------------------------

                try:

                    deliv_per = float(

                        parts[6].strip()

                    )

                except (

                    ValueError,

                    TypeError

                ):

                    continue


                rows.append(

                    {

                        "SYMBOL":
                            symbol,

                        "TIMESTAMP":
                            file_date,

                        "MTO_QTY_TRADED":
                            qty_traded,

                        "DELIV_QTY":
                            deliv_qty,

                        "DELIV_PER":
                            deliv_per

                    }

                )


            # ==========================================================
            # ADD FILE
            # ==========================================================

            if rows:

                mto_frames.append(

                    pd.DataFrame(

                        rows

                    )

                )


        # ==============================================================
        # SAFETY CHECK
        # ==============================================================

        if not mto_frames:

            raise ValueError(

                "RAW MTO files were found, but no valid "

                "EQ MTO records could be parsed."

            )


        # ==============================================================
        # COMBINE
        # ==============================================================

        mto = pd.concat(

            mto_frames,

            ignore_index=True

        )


        # ==============================================================
        # NORMALIZE MTO
        # ==============================================================

        mto["SYMBOL"] = (

            mto["SYMBOL"]

            .astype(str)

            .str.strip()

            .str.upper()

        )


        mto["TIMESTAMP"] = pd.to_datetime(

            mto["TIMESTAMP"],

            errors="coerce"

        ).dt.date


        # ==============================================================
        # KEEP ONLY BHAVCOPY SYMBOL/DATE PAIRS
        # ==============================================================

        valid_pairs = (

            history[

                [

                    "SYMBOL",

                    "TIMESTAMP"

                ]

            ]

            .drop_duplicates()

        )


        mto = mto.merge(

            valid_pairs,

            on=[

                "SYMBOL",

                "TIMESTAMP"

            ],

            how="inner"

        )


        # ==============================================================
        # REMOVE DUPLICATES
        # ==============================================================

        mto = (

            mto

            .drop_duplicates(

                subset=[

                    "SYMBOL",

                    "TIMESTAMP"

                ],

                keep="last"

            )

        )


        # ==============================================================
        # KEEP REQUIRED COLUMNS
        # ==============================================================

        mto = mto[

            [

                "SYMBOL",

                "TIMESTAMP",

                "MTO_QTY_TRADED",

                "DELIV_QTY",

                "DELIV_PER"

            ]

        ]


        # ==============================================================
        # MERGE
        # ==============================================================

        history = history.merge(

            mto,

            on=[

                "SYMBOL",

                "TIMESTAMP"

            ],

            how="left"

        )


        # ==============================================================
        # DELIVERY COVERAGE
        # ==============================================================

        delivery_coverage = (

            history["DELIV_PER"]

            .notna()

            .mean()

        )


        # ==============================================================
        # SUMMARY
        # ==============================================================

        print(

            "\nMTO merge summary:"

        )


        print(

            f"  Bhavcopy rows : "

            f"{len(history):,}"

        )


        print(

            f"  MTO rows      : "

            f"{len(mto):,}"

        )


        print(

            f"  Delivery coverage : "

            f"{delivery_coverage:.2%}"

        )


        # ==============================================================
        # SAFETY CHECK
        # ==============================================================

        if delivery_coverage == 0:

            raise ValueError(

                "MTO merge produced zero DELIV_PER values. "

                "Check SYMBOL/TIMESTAMP alignment."

            )


        return history


    # ==================================================================
    # RSI
    # ==================================================================

    def _add_rsi(
        self,
        history: pd.DataFrame
    ) -> pd.DataFrame:

        period = self.config.rsi_period


        def calculate_rsi(
            close_prices: pd.Series
        ) -> pd.Series:

            delta = close_prices.diff()


            gain = delta.clip(

                lower=0

            )


            loss = (

                -delta.clip(

                    upper=0

                )

            )


            average_gain = gain.ewm(

                alpha=1 / period,

                adjust=False,

                min_periods=period

            ).mean()


            average_loss = loss.ewm(

                alpha=1 / period,

                adjust=False,

                min_periods=period

            ).mean()


            relative_strength = (

                average_gain

                /

                average_loss

            )


            rsi = (

                100

                -

                (

                    100

                    /

                    (

                        1

                        +

                        relative_strength

                    )

                )

            )


            return rsi


        history["RSI_14"] = (

            history

            .groupby(

                "SYMBOL"

            )["CLOSE"]

            .transform(

                calculate_rsi

            )

        )


        return history


    # ==================================================================
    # MOVING AVERAGES
    # ==================================================================

    def _add_moving_averages(
        self,
        history: pd.DataFrame
    ) -> pd.DataFrame:

        history["EMA20"] = (

            history

            .groupby(

                "SYMBOL"

            )["CLOSE"]

            .transform(

                lambda close_prices:

                calculate_ema(

                    close_prices,

                    self.config.ema_fast_period

                )

            )

        )


        history["EMA50"] = (

            history

            .groupby(

                "SYMBOL"

            )["CLOSE"]

            .transform(

                lambda close_prices:

                calculate_ema(

                    close_prices,

                    self.config.ema_slow_period

                )

            )

        )


        return history


    # ==================================================================
    # DIRECTION
    # ==================================================================

    def _classify_direction(
        self,
        history: pd.DataFrame
    ) -> pd.DataFrame:

        history["DIRECTION"] = "UNKNOWN"


        history.loc[

            (

                history["CLOSE"]

                >

                history["EMA20"]

            )

            &

            (

                history["EMA20"]

                >

                history["EMA50"]

            ),

            "DIRECTION"

        ] = "STRONG_UPTREND"


        history.loc[

            (

                history["EMA20"]

                >

                history["CLOSE"]

            )

            &

            (

                history["CLOSE"]

                >

                history["EMA50"]

            ),

            "DIRECTION"

        ] = "PULLBACK"


        history.loc[

            (

                history["EMA20"]

                >

                history["EMA50"]

            )

            &

            (

                history["EMA50"]

                >

                history["CLOSE"]

            ),

            "DIRECTION"

        ] = "EARLY_WEAKNESS"


        history.loc[

            (

                history["CLOSE"]

                <

                history["EMA20"]

            )

            &

            (

                history["EMA20"]

                <

                history["EMA50"]

            ),

            "DIRECTION"

        ] = "DOWNTREND"


        return history


    # ==================================================================
    # DELIVERY FEATURES
    # ==================================================================

    def _add_delivery_features(
        self,
        history: pd.DataFrame
    ) -> pd.DataFrame:

        history["DELIVERY_AVG_5"] = (

            history

            .groupby(

                "SYMBOL"

            )["DELIV_PER"]

            .transform(

                lambda delivery:

                delivery.rolling(

                    window=self.config.delivery_short_window,

                    min_periods=self.config.delivery_short_window

                ).mean()

            )

        )


        history["DELIVERY_AVG_20"] = (

            history

            .groupby(

                "SYMBOL"

            )["DELIV_PER"]

            .transform(

                lambda delivery:

                delivery.rolling(

                    window=self.config.delivery_medium_window,

                    min_periods=self.config.delivery_medium_window

                ).mean()

            )

        )


        history["DELIVERY_AVG_60"] = (

            history

            .groupby(

                "SYMBOL"

            )["DELIV_PER"]

            .transform(

                lambda delivery:

                delivery.rolling(

                    window=self.config.delivery_long_window,

                    min_periods=self.config.delivery_long_window

                ).mean()

            )

        )


        history["DELIVERY_RATIO_5_20"] = (

            history["DELIVERY_AVG_5"]

            /

            history["DELIVERY_AVG_20"]

        )


        history["DELIVERY_RATIO_20_60"] = (

            history["DELIVERY_AVG_20"]

            /

            history["DELIVERY_AVG_60"]

        )


        return history


    # ==================================================================
    # VOLUME FEATURES
    # ==================================================================

    def _add_volume_features(
        self,
        history: pd.DataFrame
    ) -> pd.DataFrame:

        history["VOLUME_AVG_5"] = (

            history

            .groupby(

                "SYMBOL"

            )["TOTTRDQTY"]

            .transform(

                lambda volume:

                volume.rolling(

                    window=self.config.volume_short_window,

                    min_periods=self.config.volume_short_window

                ).mean()

            )

        )


        history["VOLUME_AVG_20"] = (

            history

            .groupby(

                "SYMBOL"

            )["TOTTRDQTY"]

            .transform(

                lambda volume:

                volume.rolling(

                    window=self.config.volume_medium_window,

                    min_periods=self.config.volume_medium_window

                ).mean()

            )

        )


        history["VOLUME_AVG_60"] = (

            history

            .groupby(

                "SYMBOL"

            )["TOTTRDQTY"]

            .transform(

                lambda volume:

                volume.rolling(

                    window=self.config.volume_long_window,

                    min_periods=self.config.volume_long_window

                ).mean()

            )

        )


        history["VOLUME_RATIO_5_20"] = (

            history["VOLUME_AVG_5"]

            /

            history["VOLUME_AVG_20"]

        )


        history["VOLUME_RATIO_20_60"] = (

            history["VOLUME_AVG_20"]

            /

            history["VOLUME_AVG_60"]

        )


        return history


    # ==================================================================
    # KEEP LATEST TRADING DAY
    # ==================================================================

    def _keep_latest_trading_day(
        self,
        history: pd.DataFrame
    ) -> pd.DataFrame:

        latest_date = history["TIMESTAMP"].max()


        history = history[

            history["TIMESTAMP"]

            == latest_date

        ].copy()


        history = history.reset_index(

            drop=True

        )


        return history


    # ==================================================================
    # DELIVERY SCORE
    # ==================================================================

    def _calculate_delivery_score(
        self,
        history: pd.DataFrame
    ) -> pd.DataFrame:

        history["DELIVERY_SCORE"] = (

            self.config.delivery_recent_weight

            *

            history["DELIVERY_RATIO_5_20"]

            +

            self.config.delivery_medium_weight

            *

            history["DELIVERY_RATIO_20_60"]

        )


        return history


    # ==================================================================
    # VOLUME SCORE
    # ==================================================================

    def _calculate_volume_score(
        self,
        history: pd.DataFrame
    ) -> pd.DataFrame:

        history["VOLUME_SCORE"] = (

            self.config.volume_recent_weight

            *

            history["VOLUME_RATIO_5_20"]

            +

            self.config.volume_medium_weight

            *

            history["VOLUME_RATIO_20_60"]

        )


        return history


    # ==================================================================
    # FINAL SCORE
    # ==================================================================

    def _calculate_final_score(
        self,
        history: pd.DataFrame
    ) -> pd.DataFrame:

        history["FINAL_SCORE"] = (

            self.config.delivery_weight

            *

            history["DELIVERY_SCORE"]

            +

            self.config.volume_weight

            *

            history["VOLUME_SCORE"]

        )


        return history


    # ==================================================================
    # RANK
    # ==================================================================

    def _rank_recommendations(
        self,
        history: pd.DataFrame
    ) -> pd.DataFrame:

        ranked = history.sort_values(

            by="FINAL_SCORE",

            ascending=False

        ).copy()


        selected = []


        # --------------------------------------------------------------
        # 1. STRONG UPTREND
        # --------------------------------------------------------------

        strong_uptrend = ranked[

            ranked["DIRECTION"]

            ==

            "STRONG_UPTREND"

        ].head(3)


        selected.append(

            strong_uptrend

        )


        selected_symbols = set(

            strong_uptrend["SYMBOL"]

        )


        # --------------------------------------------------------------
        # 2. PULLBACK
        # --------------------------------------------------------------

        pullback = ranked[

            (

                ranked["DIRECTION"]

                ==

                "PULLBACK"

            )

            &

            (

                ~ranked["SYMBOL"].isin(

                    selected_symbols

                )

            )

        ].head(3)


        selected.append(

            pullback

        )


        selected_symbols.update(

            pullback["SYMBOL"]

        )


        # --------------------------------------------------------------
        # 3. FILL REMAINING SLOTS
        # --------------------------------------------------------------

        remaining_slots = (

            self.config.top_n

            -

            (

                len(strong_uptrend)

                +

                len(pullback)

            )

        )


        if remaining_slots > 0:

            remaining = ranked[

                ~

                ranked["SYMBOL"].isin(

                    selected_symbols

                )

            ].head(

                remaining_slots

            )


            selected.append(

                remaining

            )


        # --------------------------------------------------------------
        # COMBINE
        # --------------------------------------------------------------

        recommendations = pd.concat(

            selected,

            ignore_index=True

        )


        return recommendations.reset_index(

            drop=True

        )