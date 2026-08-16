# -*- coding: utf-8 -*-
"""
Created on Mon Jul  6 16:11:47 2026

@author: mohak
"""

# -*- coding: utf-8 -*-

from datetime import date

import pandas as pd

import numpy as np

from config.paths import (
    PROCESSED_BHAVCOPY_DIRECTORY,
    MASTER_UNIVERSE_FILE
)

from indicators.ema_engine import calculate_ema


from strategies.strategy2.strategy2_config import (
    Strategy2Config
)


class Strategy2:

    def __init__(
        self,
        config: Strategy2Config
    ):

        self.config = config

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
    
        Returns
        -------
        pd.DataFrame
            Top-ranked recommendations.
        """
    
        # Production: load history internally
        if history is None:
    
            history = self._load_history(
                recommendation_date
            )
    
        # Prevent modifying the caller's DataFrame
        history = history.copy()
    
        # Feature Engineering
        history = self._build_features(
            history
        )
    
        # Keep only recommendation date
        history = self._keep_latest_trading_day(
            history
        )
    
        # Score Calculation
        history = self._calculate_delivery_score(
            history
        )
    
        history = self._calculate_volume_score(
            history
        )
    
        history = self._calculate_final_score(
            history
        )
    
        # Remove rows without enough history
        history = history.dropna(
            subset=["FINAL_SCORE"]
        )
    
        # Ranking
        history = self._rank_recommendations(
            history
        )
    
        return history

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
    
    def _load_history(
        self,
        recommendation_date: date
    ) -> pd.DataFrame:
    
        parquet_files = []
    
        for file in PROCESSED_BHAVCOPY_DIRECTORY.glob(
            "*.parquet"
        ):
    
            file_date = date.fromisoformat(
                f"{file.stem[-4:]}-{file.stem[-6:-4]}-{file.stem[-8:-6]}"
            )
    
            if file_date <= recommendation_date:
    
                parquet_files.append(
                    (
                        file_date,
                        file
                    )
                )
    
        parquet_files = [
    
            file
    
            for _, file in sorted(
    
                parquet_files,
    
                key=lambda x: x[0],
    
                reverse=True
    
            )[:self.config.history_window]
    
        ]
    
        history = pd.concat(
    
            [
    
                pd.read_parquet(file)
    
                for file in parquet_files
    
            ],
    
            ignore_index=True
    
        )
    
        master_universe = pd.read_csv(
            MASTER_UNIVERSE_FILE
        )
    
        history = history[
    
            history["SYMBOL"].isin(
    
                master_universe["SYMBOL"]
    
            )
    
        ]
    
        history = history.sort_values(
    
            by=[
                "SYMBOL",
                "TIMESTAMP"
            ]
    
        ).reset_index(
    
            drop=True
    
        )
    
        return history
    
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
                / average_loss
            )
    
            rsi = (
                100
                -
                (
                    100
                    /
                    (
                        1
                        + relative_strength
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
    def _add_moving_averages(
    
        self,
    
        history: pd.DataFrame
    
    ) -> pd.DataFrame:
    
        history["EMA20"] = (
        
            history
        
            .groupby("SYMBOL")["CLOSE"]
        
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
        
            .groupby("SYMBOL")["CLOSE"]
        
            .transform(
        
                lambda close_prices:
        
                calculate_ema(
        
                    close_prices,
        
                    self.config.ema_slow_period
        
                )
        
            )
        
        )
    
        return history
    
    def _classify_direction(
        self,
        history: pd.DataFrame
    ) -> pd.DataFrame:
    
        history["DIRECTION"] = "UNKNOWN"
    
        history.loc[
            (
                (history["CLOSE"] > history["EMA20"])
                &
                (history["EMA20"] > history["EMA50"])
            ),
            "DIRECTION"
        ] = "STRONG_UPTREND"
    
        history.loc[
            (
                (history["EMA20"] > history["CLOSE"])
                &
                (history["CLOSE"] > history["EMA50"])
            ),
            "DIRECTION"
        ] = "PULLBACK"
    
        history.loc[
            (
                (history["EMA20"] > history["EMA50"])
                &
                (history["EMA50"] > history["CLOSE"])
            ),
            "DIRECTION"
        ] = "EARLY_WEAKNESS"
    
        history.loc[
            (
                (history["CLOSE"] < history["EMA20"])
                &
                (history["EMA20"] < history["EMA50"])
            ),
            "DIRECTION"
        ] = "DOWNTREND"
    
        return history
    
    def _add_delivery_features(

        self,
    
        history: pd.DataFrame
    
    ) -> pd.DataFrame:
            
        history["DELIVERY_AVG_5"] = (
        
            history
        
            .groupby("SYMBOL")["DELIV_PER"]
        
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
        
            .groupby("SYMBOL")["DELIV_PER"]
        
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
        
            .groupby("SYMBOL")["DELIV_PER"]
        
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
    
    def _add_volume_features(
    
        self,
    
        history: pd.DataFrame
    
    ) -> pd.DataFrame:
    
        history["VOLUME_AVG_5"] = (
    
            history
    
            .groupby("SYMBOL")["TOTTRDQTY"]
    
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
    
            .groupby("SYMBOL")["TOTTRDQTY"]
    
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
    
            .groupby("SYMBOL")["TOTTRDQTY"]
    
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
    
    def _keep_latest_trading_day(
    
        self,
    
        history: pd.DataFrame
    
    ) -> pd.DataFrame:
    
        latest_date = history["TIMESTAMP"].max()
    
        history = history[
    
            history["TIMESTAMP"] == latest_date
    
        ].copy()
    
        history = history.reset_index(
    
            drop=True
    
        )
    
        return history
        
    def _calculate_delivery_score(
        self,
        history: pd.DataFrame
    ) -> pd.DataFrame:
    
        history["DELIVERY_SCORE"] = (
    
            self.config.delivery_recent_weight
            * history["DELIVERY_RATIO_5_20"]
    
            +
    
            self.config.delivery_medium_weight
            * history["DELIVERY_RATIO_20_60"]
    
        )
    
        return history
    
    def _calculate_volume_score(
        self,
        history: pd.DataFrame
    ) -> pd.DataFrame:
    
        history["VOLUME_SCORE"] = (
    
            self.config.volume_recent_weight
            * history["VOLUME_RATIO_5_20"]
    
            +
    
            self.config.volume_medium_weight
            * history["VOLUME_RATIO_20_60"]
    
        )
    
        return history
    
    def _calculate_final_score(
        self,
        history: pd.DataFrame
    ) -> pd.DataFrame:
    
        history["FINAL_SCORE"] = (
    
            self.config.delivery_weight
            * history["DELIVERY_SCORE"]
    
            +
    
            self.config.volume_weight
            * history["VOLUME_SCORE"]
    
        )
    
        return history
    
    def _rank_recommendations(
        self,
        history: pd.DataFrame
    ) -> pd.DataFrame:

        # Sort all candidates by final score
        ranked = history.sort_values(
            by="FINAL_SCORE",
            ascending=False
        ).copy()

        selected = []

        # ---------------------------------------------------------
        # 1. Top 3 STRONG_UPTREND stocks
        # ---------------------------------------------------------
        strong_uptrend = ranked[
            ranked["DIRECTION"] == "STRONG_UPTREND"
        ].head(3)

        selected.append(strong_uptrend)

        # Keep track of already selected stocks
        selected_symbols = set(
            strong_uptrend["SYMBOL"]
        )

        # ---------------------------------------------------------
        # 2. Top 3 PULLBACK stocks
        # ---------------------------------------------------------
        pullback = ranked[
            (ranked["DIRECTION"] == "PULLBACK")
            &
            (~ranked["SYMBOL"].isin(selected_symbols))
        ].head(3)

        selected.append(pullback)

        selected_symbols.update(
            pullback["SYMBOL"]
        )

        # ---------------------------------------------------------
        # 3. Fill remaining slots using highest FINAL_SCORE
        #    without repeating already selected stocks
        # ---------------------------------------------------------
        remaining_slots = self.config.top_n - (
            len(strong_uptrend) + len(pullback)
        )

        if remaining_slots > 0:

            remaining = ranked[
                ~ranked["SYMBOL"].isin(selected_symbols)
            ].head(remaining_slots)

            selected.append(remaining)

        # ---------------------------------------------------------
        # Combine selections
        # ---------------------------------------------------------
        recommendations = pd.concat(
            selected,
            ignore_index=True
        )

        return recommendations.reset_index(drop=True)
    
