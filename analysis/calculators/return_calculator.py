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
        nifty_entry_price = row["nifty_50_price"]

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

        nifty_df = yf.download(
            tickers="^NSEI",
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

        if isinstance(
            nifty_df.columns,
            pd.MultiIndex
        ):
            nifty_df.columns = (
                nifty_df.columns
                .get_level_values(0)
            )

        if len(price_df) < 2:
            continue

        if len(nifty_df) < 2:
            continue

        price_df = price_df.reset_index()
        nifty_df = nifty_df.reset_index()

        # =====================================
        # BTST RETURN
        # =====================================

        btst_high = price_df.iloc[1]["High"]

        btst_return = (
            (btst_high - entry_price)
            / entry_price
        ) * 100

        nifty_btst_high = (
            nifty_df.iloc[1]["High"]
        )

        nifty_btst_return = (
            (
                nifty_btst_high
                - nifty_entry_price
            )
            / nifty_entry_price
        ) * 100

        btst_outperformance = (
            btst_return
            - nifty_btst_return
        )

        # =====================================
        # 7 DAY RETURN
        # =====================================

        if (
            len(price_df) >= 8
            and len(nifty_df) >= 8
        ):

            day_7_close = (
                price_df.iloc[7]["Close"]
            )

            return_7d = (
                (
                    day_7_close
                    - entry_price
                )
                / entry_price
            ) * 100

            nifty_day_7_close = (
                nifty_df.iloc[7]["Close"]
            )

            nifty_7d_return = (
                (
                    nifty_day_7_close
                    - nifty_entry_price
                )
                / nifty_entry_price
            ) * 100

            outperformance_7d = (
                return_7d
                - nifty_7d_return
            )

        else:

            return_7d = None
            outperformance_7d = None

        # =====================================
        # CURRENT RETURN
        # =====================================

        latest_close = (
            price_df.iloc[-1]["Close"]
        )

        return_till_today = (
            (
                latest_close
                - entry_price
            )
            / entry_price
        ) * 100

        nifty_latest_close = (
            nifty_df.iloc[-1]["Close"]
        )

        nifty_current_return = (
            (
                nifty_latest_close
                - nifty_entry_price
            )
            / nifty_entry_price
        ) * 100

        current_outperformance = (
            return_till_today
            - nifty_current_return
        )

        # =====================================
        # HIGHEST RETURN
        # =====================================

        highest_high = (
            price_df["High"].max()
        )

        highest_return = ((highest_high - entry_price) / entry_price) * 100

        # =====================================
        # LOWEST RETURN
        # =====================================

        lowest_low = (
            price_df["Low"].min()
        )

        lowest_return = (
            (
                lowest_low
                - entry_price
            )
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

                "btst_outperformance_pct": round(
                    btst_outperformance, 2
                ),

                "return_7d_pct": (
                    round(return_7d, 2)
                    if return_7d is not None
                    else None
                ),

                "outperformance_7d_pct": (
                    round(
                        outperformance_7d, 2
                    )
                    if outperformance_7d is not None
                    else None
                ),

                "return_14d_pct": round(
                    return_till_today, 2
                ),

                "outperformance_14d_pct": round(
                    current_outperformance, 2
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