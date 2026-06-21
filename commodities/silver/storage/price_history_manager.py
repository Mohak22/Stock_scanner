# -*- coding: utf-8 -*-
"""
Created on Sun Jun 21 21:31:17 2026

@author: mohak
"""

from datetime import date

import pandas as pd


def save_price(
    file_path,
    price: int
) -> None:

    file_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    today = (
        date.today()
        .isoformat()
    )

    try:

        df = pd.read_csv(
            file_path
        )

    except FileNotFoundError:

        df = pd.DataFrame(
            columns=[
                "date",
                "price"
            ]
        )

    if today in df["date"].values:

        df.loc[
            df["date"] == today,
            "price"
        ] = price

    else:

        new_row = pd.DataFrame(
            [{
                "date": today,
                "price": price
            }]
        )

        df = pd.concat(
            [df, new_row],
            ignore_index=True
        )

    df.to_csv(
        file_path,
        index=False
    )