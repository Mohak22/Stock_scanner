# -*- coding: utf-8 -*-
"""
Created on Sun May 31 13:53:54 2026

@author: mohak
"""

from strategies.strategy1.strategy1_main import run_strategy_1

from selector.select_best_strategy import select_best_strategy

from reports.final_mail_sender import send_final_email

# =========================================================
# CONFIGURATION
# =========================================================

SAVE_OUTPUT = True

# =========================================================
# RUN STRATEGIES
# =========================================================

strategy_results = [
    run_strategy_1(SAVE_OUTPUT)
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