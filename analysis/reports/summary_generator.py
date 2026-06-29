# -*- coding: utf-8 -*-
"""
Created on Sun Jun 14 14:28:08 2026

@author: mohak
"""

import pandas as pd

def create_summary(
    analysis_df: pd.DataFrame,
    strategy_name: str
) -> pd.DataFrame:

    return pd.DataFrame(
        {
            "strategy_name": [strategy_name],

            "total_picks": [
                len(analysis_df)
            ],

            # =====================================
            # BTST
            # =====================================

            "avg_btst_return_pct": [
                round(
                    analysis_df[
                        "btst_return_pct"
                    ].mean(),
                    2
                )
            ],

            "btst_win_rate_pct": [
                round(
                    (
                        analysis_df[
                            "btst_return_pct"
                        ] > 0
                    ).mean()
                    * 100,
                    2
                )
            ],

            "avg_btst_outperformance_pct": [
                round(
                    analysis_df[
                        "btst_outperformance_pct"
                    ].mean(),
                    2
                )
            ],

            # =====================================
            # 7 DAY
            # =====================================

            "avg_7d_return_pct": [
                round(
                    analysis_df[
                        "return_7d_pct"
                    ].mean(),
                    2
                )
            ],

            "return_7d_win_rate_pct": [
                round(
                    (
                        analysis_df[
                            "return_7d_pct"
                        ] > 0
                    ).mean()
                    * 100,
                    2
                )
            ],

            "avg_7d_outperformance_pct": [
                round(
                    analysis_df[
                        "outperformance_7d_pct"
                    ].mean(),
                    2
                )
            ],

            # =====================================
            # CURRENT
            # =====================================

            "avg_14d_return_pct": [
                round(
                    analysis_df[
                        "return_14d_pct"
                    ].mean(),
                    2
                )
            ],

            "return_14d_win_rate_pct": [
                round(
                    (
                        analysis_df[
                            "return_14d_pct"
                        ] > 0
                    ).mean()
                    * 100,
                    2
                )
            ],

            "avg_14d_outperformance_pct": [
                round(
                    analysis_df[
                        "outperformance_14d_pct"
                    ].mean(),
                    2
                )
            ],

            # =====================================
            # EXTREMES
            # =====================================

            "avg_highest_return_pct": [
                round(
                    analysis_df[
                        "highest_return_pct"
                    ].mean(),
                    2
                )
            ],

            "avg_lowest_return_pct": [
                round(
                    analysis_df[
                        "lowest_return_pct"
                    ].mean(),
                    2
                )
            ]
        }
    )   