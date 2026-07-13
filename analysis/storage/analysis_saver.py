# -*- coding: utf-8 -*-
"""
Created on Sun Jun 14 14:31:30 2026

@author: mohak
"""

from datetime import date
import pandas as pd

from config.paths import DATA_REPOSITORY

def save_analysis(
    analysis_df: pd.DataFrame,
    strategy_name: str
) -> None:

    output_folder = (
        DATA_REPOSITORY
        / "analysis"
        / strategy_name
    )

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    output_file = (
        output_folder
        / f"analysis_{date.today()}.xlsx"
    )

    columns_to_remove = [
        "strategy_name",
        "nifty_50_price",
        "sector_price",
        "ema_50",
        "rsi_9",
        "previous_rsi_14"
    ]

    analysis_df = analysis_df.drop(
        columns=columns_to_remove,
        errors="ignore"
    )

    analysis_df.to_excel(
        output_file,
        index=False
    )

    print(
        f"Saved: {output_file}"
    )