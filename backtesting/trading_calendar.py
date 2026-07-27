# -*- coding: utf-8 -*-
"""
Created on Mon Jul 20 21:57:16 2026

@author: mohak
"""

import pandas as pd


class TradingCalendar:

    def get_recommendation_dates(
        self,
        history: pd.DataFrame,
        start_date,
        end_date
    ) -> list[pd.Timestamp]:

        trading_dates = (

            history["TIMESTAMP"]

            .drop_duplicates()

            .sort_values()

        )

        trading_dates = trading_dates[

            (trading_dates >= pd.Timestamp(start_date))

            &

            (trading_dates <= pd.Timestamp(end_date))

        ]

        return trading_dates.tolist()