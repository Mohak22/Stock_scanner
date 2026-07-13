# -*- coding: utf-8 -*-
"""
Created on Sun May 31 13:53:54 2026

@author: mohak
"""

from datetime import date

from strategies.strategy1.strategy1 import run_strategy_1

# from strategies.strategy2.strategy2 import run_strategy_2

from selector.select_best_strategy import select_best_strategy

from reports.final_mail_sender import send_final_email

from processing.daily_data_processing import Daily_Data_Preparation
# =========================================================
# CONFIGURATION
# =========================================================

SAVE_OUTPUT = True

TODAY = date.today()

HISTORY_WINDOW = 60

Daily_Data_Preparation().run(
    recommendation_date=TODAY,
    history_window=HISTORY_WINDOW

)
# =========================================================
# RUN STRATEGIES
# =========================================================

strategy_results = [
    run_strategy_1(SAVE_OUTPUT)
    
    # run_strategy_2(
    #     recommendation_date=TODAY,
    #     history_window=HISTORY_WINDOW,
    #     save_output_flag=SAVE_OUTPUT
    # )
]

# =========================================================
# SELECT FINAL RECOMMENDATIONS
# =========================================================

final_result = select_best_strategy(strategy_results, SAVE_OUTPUT)

# =========================================================
# SEND DAILY EMAIL
# =========================================================

send_final_email(
    final_result
)