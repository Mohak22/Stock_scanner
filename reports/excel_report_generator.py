# -*- coding: utf-8 -*-
"""
Created on Mon May 25 16:06:37 2026

@author: mohak
"""

from __future__ import annotations

import pandas as pd

from pathlib import Path

from openpyxl.utils import (
    get_column_letter
)

from config.paths import DATA_REPOSITORY

# =========================================================
# GENERATE EXCEL REPORT
# =========================================================

def generate_excel_report(
    weak_stock_dataframe: pd.DataFrame
) -> None:

    report_path = (
        "reports/daily_scan_report.xlsx"
    )

    with pd.ExcelWriter(
        report_path,
        engine="openpyxl"
    ) as writer:

        weak_stock_dataframe.to_excel(
            writer,
            sheet_name="Shortlisted Stocks",
            index=False
        )

        worksheet = writer.sheets[
            "Shortlisted Stocks"
        ]

        # =================================================
        # AUTO ADJUST COLUMN WIDTH
        # =================================================

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

    print(
        "\nExcel report generated."
    )


# =========================================================
# SAVE OUTPUT CSV
# =========================================================

def save_output(
    dataframe: pd.DataFrame,
    folder_name: str,
    file_name: str,
    save_output: bool
) -> None:

    if not save_output:

        print(
            "\nSAVE OUTPUT DISABLED"
        )

        return

    if dataframe.empty:

        print(
            "\nEMPTY DATAFRAME - NOTHING SAVED"
        )

        return

    save_folder = (
    
        DATA_REPOSITORY
        / folder_name
    
    )

    save_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    file_path = (
        save_folder
        / file_name
    )

    suffix = file_path.suffix.lower()

    if suffix == ".csv":

        dataframe.to_csv(
            file_path,
            index=False
        )

    elif suffix == ".parquet":

        dataframe.to_parquet(
            file_path,
            index=False
        )

    else:

        raise ValueError(
            f"Unsupported file type : {suffix}"
        )

    print(
        f"\nSaved : {file_path}"
    )