# -*- coding: utf-8 -*-
"""
Created on Mon Jun 15 18:39:16 2026

@author: mohak
"""

from openpyxl.utils import get_column_letter


def autofit_columns(
    worksheet
) -> None:

    for column in worksheet.columns:

        max_length = 0

        column_letter = (
            get_column_letter(
                column[0].column
            )
        )

        for cell in column:

            try:

                cell_length = len(
                    str(cell.value)
                )

                max_length = max(
                    max_length,
                    cell_length
                )

            except Exception:

                pass

        worksheet.column_dimensions[
            column_letter
        ].width = (
            max_length + 2, 40
        )