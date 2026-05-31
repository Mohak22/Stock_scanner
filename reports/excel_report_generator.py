# -*- coding: utf-8 -*-
"""
Created on Mon May 25 16:06:37 2026

@author: mohak
"""

from __future__ import annotations

import pandas as pd
from pathlib import Path

DATA_REPO_PATH = Path(
    "../STOCK_SCANNER_DATA"
)

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

    print(
        "\nExcel report generated."
    )
    

def save_output(
    dataframe: pd.DataFrame,
    folder_name: str,
    file_name: str,
    save_output: bool
) -> None:

    if not save_output:

        print("\nSAVE OUTPUT DISABLED")
        return

    if dataframe.empty:

        print("\nEMPTY DATAFRAME - NOTHING SAVED")
        return

    save_folder = (
        DATA_REPO_PATH
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

    dataframe.to_csv(
        file_path,
        index=False
    )

    print(
        f"\nSaved: {file_path}"
    )
