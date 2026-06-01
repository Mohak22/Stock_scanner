# -*- coding: utf-8 -*-
"""
Created on Mon Jun  1 14:27:40 2026

@author: mohak
"""

import pandas as pd


def calculate_ema(

    close_prices: pd.Series,

    period: int
) -> pd.Series:

    ema_series = close_prices.ewm(

        span=period,

        adjust=False

    ).mean()

    return ema_series