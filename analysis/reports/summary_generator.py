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
            "total_picks": [len(analysis_df)],
            "avg_btst_return_pct": [
                round(
                    analysis_df[
                        "btst_return_pct"
                    ].mean(),
                    2
                )
            ],
            "avg_3d_return_pct": [
                round(
                    analysis_df[
                        "return_3d_pct"
                    ].mean(),
                    2
                )
            ],
            "avg_current_return_pct": [
                round(
                    analysis_df[
                        "return_till_today_pct"
                    ].mean(),
                    2
                )
            ],
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
            ],
            "win_rate_pct": [
                round(
                    (
                        analysis_df[
                            "return_till_today_pct"
                        ] > 0
                    ).mean()
                    * 100,
                    2
                )
            ]
        }
    )