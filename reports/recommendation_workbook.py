# -*- coding: utf-8 -*-
"""
Created on Sun Jun 28 14:25:52 2026

@author: mohak
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime

import pandas as pd

from openpyxl.utils import get_column_letter

from config.paths import (
    FINAL_RECOMMENDATIONS_FOLDER,
    STRATEGIES_FOLDER,
    DATA_REPOSITORY
)

TEMP_FOLDER = (
    DATA_REPOSITORY
    / "temp"
)

TEMP_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)

REPORT_PATH = (
    TEMP_FOLDER
    / "recommendation_workbook.xlsx"
)

# =========================================================
# AUTO ADJUST WIDTH
# =========================================================

def auto_adjust_columns(
    worksheet
) -> None:

    for column_cells in worksheet.columns:

        max_length = max(

            len(str(cell.value))
            if cell.value is not None
            else 0

            for cell in column_cells
        )

        column_letter = (
            get_column_letter(
                column_cells[0].column
            )
        )

        worksheet.column_dimensions[
            column_letter
        ].width = max_length + 4


# =========================================================
# GENERATE WORKBOOK
# =========================================================

def generate_recommendation_workbook() -> Path:

    current_date = datetime.now().strftime(
        "%Y-%m-%d"
    )
    
    final_file = (
        FINAL_RECOMMENDATIONS_FOLDER
        / f"final_recommendations_{current_date}.csv"
    )
    
    if final_file.exists():
    
        final_dataframe = pd.read_csv(
            final_file
        )
    
    else:
    
        final_dataframe = pd.DataFrame()
    
    with pd.ExcelWriter(
        REPORT_PATH,
        engine="openpyxl"
    ) as writer:

        # =============================================
        # FINAL RECOMMENDATIONS
        # =============================================

        final_dataframe.to_excel(
            writer,
            sheet_name="FINAL_RECOMMENDATIONS",
            index=False
        )

        auto_adjust_columns(
            writer.sheets[
                "FINAL_RECOMMENDATIONS"
            ]
        )

        # =============================================
        # STRATEGY SHEETS
        # =============================================
        
        strategy_outputs_found = False
        
        if STRATEGIES_FOLDER.exists():

            strategy_folders = sorted(

                folder

                for folder in STRATEGIES_FOLDER.iterdir()

                if folder.is_dir()
            )
            
            for strategy_folder in strategy_folders:

                strategy_file = (
                
                    strategy_folder
                
                    / f"{strategy_folder.name}_{current_date}.csv"
                )
                
                if not strategy_file.exists():
                
                    continue
                
                dataframe = pd.read_csv(
                    strategy_file
                )
                
                if dataframe.empty:
                
                    continue
                
                strategy_outputs_found = True
                
                sheet_name = (
                    strategy_folder.name
                    .upper()
                )

                dataframe.to_excel(

                    writer,

                    sheet_name=sheet_name,

                    index=False
                )

                auto_adjust_columns(

                    writer.sheets[
                        sheet_name
                    ]
                )

    print(
        "\nRecommendation workbook generated."
    )

    return {
    
        "workbook_path":
            REPORT_PATH,
    
        "final_recommendations_found":
            not final_dataframe.empty,
    
        "strategy_outputs_found":
            strategy_outputs_found
    }