# -*- coding: utf-8 -*-
"""
Created on Sun Jun 14 12:28:48 2026

@author: mohak
"""

from datetime import date, timedelta

import pandas as pd
import yfinance as yf

def calculate_returns(
    recommendations_df: pd.DataFrame
) -> pd.DataFrame:

    analysis_rows = []

    today = date.today()

    for _, row in recommendations_df.iterrows():

        symbol = row["stock_symbol"]
        ticker = f"{symbol}.NS"

        entry_price = row["entry_close_price"]

        recommendation_date = pd.to_datetime(
            row["recommendation_date"]
        )

        price_df = yf.download(
            tickers=ticker,
            start=recommendation_date.date(),
            end=today + timedelta(days=1),
            progress=False,
            auto_adjust=False
        )

        if isinstance(
            price_df.columns,
            pd.MultiIndex
        ):
            price_df.columns = (
                price_df.columns
                .get_level_values(0)
            )

        if len(price_df) < 2:
            continue

        price_df = price_df.reset_index()

        btst_high = price_df.iloc[1]["High"]

        btst_return = (
            (btst_high - entry_price)
            / entry_price
        ) * 100

        if len(price_df) >= 4:
            day_3_close = price_df.iloc[3]["Close"]

            return_3d = (
                (day_3_close - entry_price)
                / entry_price
            ) * 100
        else:
            return_3d = None

        latest_close = price_df.iloc[-1]["Close"]

        return_till_today = (
            (latest_close - entry_price)
            / entry_price
        ) * 100

        highest_high = (
            price_df["High"].max()
        )

        highest_return = (
            (highest_high - entry_price)
            / entry_price
        ) * 100

        lowest_low = (
            price_df["Low"].min()
        )

        lowest_return = (
            (lowest_low - entry_price)
            / entry_price
        ) * 100

        analysis_row = row.to_dict()

        analysis_row.update(
            {
                "recommendation_date": recommendation_date,
                "analysis_date": today,
                "btst_return_pct": round(
                    btst_return, 2
                ),
                "return_3d_pct": (
                    round(return_3d, 2)
                    if return_3d is not None
                    else None
                ),
                "return_till_today_pct": round(
                    return_till_today, 2
                ),
                "highest_return_pct": round(
                    highest_return, 2
                ),
                "lowest_return_pct": round(
                    lowest_return, 2
                ),
            }
        )

        analysis_rows.append(
            analysis_row
        )

    return pd.DataFrame(
        analysis_rows
    )