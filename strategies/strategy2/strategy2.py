# -*- coding: utf-8 -*-
"""
Created on Sun Jul 12 10:03:24 2026

@author: mohak
"""

from datetime import date, datetime

from strategies.strategy2.accumulation import (
    Strategy2
)

from strategies.strategy2.strategy2_config import (
    Strategy2Config
)

from reports.excel_report_generator import (
    save_output
)

STRATEGY_NAME = "accumulation"


def run_strategy_2(

    recommendation_date: date,

    history_window: int,

    save_output_flag: bool

):

    config = Strategy2Config(

        history_window=history_window

    )

    strategy = Strategy2(

        config=config

    )

    recommendations = strategy.run(

        recommendation_date=recommendation_date

    )

    current_date = datetime.now().strftime(

        "%Y-%m-%d"

    )

    save_output(

        dataframe=recommendations,

        folder_name=f"strategies/{STRATEGY_NAME}",

        file_name=f"{STRATEGY_NAME}_{current_date}.csv",

        save_output=save_output_flag

    )

    return recommendations