# -*- coding: utf-8 -*-
"""
Created on Sun May 31 13:53:54 2026

@author: mohak
"""


from strategies.strategy1.strategy1_main import run_strategy_1

from selector.select_best_strategy import select_best_strategy

from reports.final_mail_sender import send_final_email

save_output_flag = True

strategy_1_result = run_strategy_1(save_output_flag)

final_result = select_best_strategy(
    [strategy_1_result], save_output_flag
)

send_final_email(
    final_result
)