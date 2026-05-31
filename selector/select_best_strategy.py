# -*- coding: utf-8 -*-
"""
Created on Sun May 31 14:17:58 2026

@author: mohak
"""

from datetime import datetime

from reports.excel_report_generator import (
    save_output
)


def select_best_strategy(
    strategy_results: list,
    save_output_flag: bool
) -> dict:

    final_result = strategy_results[0]

    recommendations = (
        final_result["recommendations"]
    )

    current_date = datetime.now().strftime(
        "%Y-%m-%d"
    )

    save_output(

        dataframe=recommendations,

        folder_name=(
            "final_recommendations"
        ),

        file_name=(
            f"final_recommendations_{current_date}.csv"
        ),

        save_output=save_output_flag
    )

    return final_result