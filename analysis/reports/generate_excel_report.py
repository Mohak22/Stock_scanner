# -*- coding: utf-8 -*-
"""
Created on Sun Jun 14 14:35:19 2026

@author: mohak
"""

import pandas as pd
from datetime import date
from pathlib import Path

from reports.summary_generator import create_summary
from config.paths import REPORT_FOLDER

def generate_excel_report(
    final_analysis_df: pd.DataFrame,
    strategy_analysis_dfs: dict
) -> Path:

    report_path = (
        REPORT_FOLDER
        / f"analysis_report_{date.today()}.xlsx"
    )

    report_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    summary_dfs = [
        create_summary(
            final_analysis_df,
            "final_recommendations"
        )
    ]

    for (
        strategy_name,
        analysis_df
    ) in strategy_analysis_dfs.items():

        summary_dfs.append(
            create_summary(
                analysis_df,
                strategy_name
            )
        )

    summary_df = pd.concat(
        summary_dfs,
        ignore_index=True
    )

    with pd.ExcelWriter(
        report_path,
        engine="openpyxl"
    ) as writer:

        summary_df.to_excel(
            writer,
            sheet_name="Summary",
            index=False
        )

        final_analysis_df.to_excel(
            writer,
            sheet_name="Final_Recommendations",
            index=False
        )

        for (
            strategy_name,
            analysis_df
        ) in strategy_analysis_dfs.items():

            if analysis_df.empty:
                continue

            analysis_df.to_excel(
                writer,
                sheet_name=strategy_name,
                index=False
            )

    return report_path