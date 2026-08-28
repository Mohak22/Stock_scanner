# -*- coding: utf-8 -*-
"""
Created on Sun May 31 13:53:54 2026

@author: mohak
"""

"""
Production Strategy Orchestrator

Responsibilities:
    1. Run active strategies.
    2. Select the best strategy.
    3. Generate/send final report.

IMPORTANT:
    Daily data preparation runs separately.

    This file assumes all required market, stock, Bhavcopy,
    MTO and processed data has already been prepared by the
    separate Daily Data Preparation workflow.
"""


from datetime import date

from strategies.strategy1.strategy1 import (
    run_strategy_1
)

from strategies.strategy2.strategy2 import (
    run_strategy_2
)

from selector.select_best_strategy import (
    select_best_strategy
)

from reports.final_mail_sender import (
    send_final_email
)


# ======================================================================
# CONFIGURATION
# ======================================================================

SAVE_OUTPUT = True

TODAY = date.today()


# ======================================================================
# RUN STRATEGIES
# ======================================================================

strategy_results = [

    # --------------------------------------------------------------
    # STRATEGY 1
    # --------------------------------------------------------------

    run_strategy_1(
        SAVE_OUTPUT
    ),


    # --------------------------------------------------------------
    # STRATEGY 2
    # --------------------------------------------------------------

    run_strategy_2(
        recommendation_date=TODAY,
        history_window=60,
        save_output_flag=SAVE_OUTPUT
    )

]


# ======================================================================
# SELECT FINAL RECOMMENDATIONS
# ======================================================================

final_result = select_best_strategy(
    strategy_results,
    SAVE_OUTPUT
)


# ======================================================================
# SEND DAILY EMAIL
# ======================================================================

send_final_email(
    final_result
)