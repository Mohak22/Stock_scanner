# -*- coding: utf-8 -*-
"""
Created on Sun Jun 14 12:26:12 2026

@author: mohak
"""

from datetime import date
from pathlib import Path

import pandas as pd


def load_recommendations(
    folder_path: Path,
    prefix: str,
    target_date: date
) -> pd.DataFrame:

    file_name = (
        f"{prefix}_{target_date}.csv"
    )

    file_path = folder_path / file_name

    if not file_path.exists():
        print(f"Missing file: {file_path}")
        return pd.DataFrame()

    return pd.read_csv(file_path)