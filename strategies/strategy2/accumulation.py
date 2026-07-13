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

from indicators.ema import calculate_ema


class Strategy2:

    HISTORY_WINDOW = 60

    EMA20_PERIOD = 20

    EMA50_PERIOD = 50
    
    DELIVERY_SHORT_WINDOW = 5

    DELIVERY_MEDIUM_WINDOW = 20
   
    DELIVERY_LONG_WINDOW = 60
    
    VOLUME_SHORT_WINDOW = 5

    VOLUME_MEDIUM_WINDOW = 20
    
    VOLUME_LONG_WINDOW = 60

    def run(
        self,
        recommendation_date: date,
        save_output: bool
    ):

        history = self._load_history(recommendation_date)

        history = self._add_moving_averages(
            history
        )

        history = self._classify_direction(
            history
        )

        history = self._add_delivery_features(
            history
        )
        
        history = self._add_volume_features(
            history
        )
        
        history = self._keep_latest_trading_day(
            history
        )
        
        history = history.replace(
        
            [np.inf, -np.inf],
        
            np.nan
        
        )
        
        return history
    
    def _load_history(
        self,  recommendation_date
    ) -> pd.DataFrame:
    
        parquet_files = sorted(
    
            PROCESSED_BHAVCOPY_DIRECTORY.glob(
                "*.parquet"
            ),
    
            reverse=True
    
        )[:self.HISTORY_WINDOW]
    
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
    
                    self.EMA20_PERIOD
    
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
    
                    self.EMA50_PERIOD
    
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
        
                    window=self.DELIVERY_SHORT_WINDOW,
        
                    min_periods=self.DELIVERY_SHORT_WINDOW
        
                ).mean()
        
            )
        
        )
            
        history["DELIVERY_AVG_20"] = (
        
            history
        
            .groupby("SYMBOL")["DELIV_PER"]
        
            .transform(
        
                lambda delivery:
        
                delivery.rolling(
        
                    window=self.DELIVERY_MEDIUM_WINDOW,
        
                    min_periods=self.DELIVERY_MEDIUM_WINDOW
        
                ).mean()
        
            )
        
        )

        history["DELIVERY_AVG_60"] = (
        
            history
        
            .groupby("SYMBOL")["DELIV_PER"]
        
            .transform(
        
                lambda delivery:
        
                delivery.rolling(
        
                    window=self.DELIVERY_LONG_WINDOW,
        
                    min_periods=self.DELIVERY_LONG_WINDOW
        
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
    
                    window=self.VOLUME_SHORT_WINDOW,
    
                    min_periods=self.VOLUME_SHORT_WINDOW
    
                ).mean()
    
            )
    
        )
    
        history["VOLUME_AVG_20"] = (
    
            history
    
            .groupby("SYMBOL")["TOTTRDQTY"]
    
            .transform(
    
                lambda volume:
    
                volume.rolling(
    
                    window=self.VOLUME_MEDIUM_WINDOW,
    
                    min_periods=self.VOLUME_MEDIUM_WINDOW
    
                ).mean()
    
            )
    
        )
    
        history["VOLUME_AVG_60"] = (
    
            history
    
            .groupby("SYMBOL")["TOTTRDQTY"]
    
            .transform(
    
                lambda volume:
    
                volume.rolling(
    
                    window=self.VOLUME_LONG_WINDOW,
    
                    min_periods=self.VOLUME_LONG_WINDOW
    
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