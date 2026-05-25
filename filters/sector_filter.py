# -*- coding: utf-8 -*-
"""
Created on Sun May 24 16:58:33 2026

@author: mohak
"""

from __future__ import annotations

import pandas as pd

# =========================================================
# FILTER WEAK SECTORS
# =========================================================

def filter_weak_sectors(
    sector_dataframe: pd.DataFrame
) -> pd.DataFrame:

    filtered_dataframe = (

        sector_dataframe[

            (sector_dataframe["RSI_14"] < 45)

            &

            (
                sector_dataframe["RSI_9"]
                <
                sector_dataframe["RSI_14"]
            )
        ]

        .sort_values(
            by="RSI_14"
        )

        .head(5)

        .reset_index(
            drop=True
        )
    )

    return filtered_dataframe