# -*- coding: utf-8 -*-
"""
Created on Mon May 25 16:06:37 2026

@author: mohak
"""

from __future__ import annotations

import pandas as pd

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