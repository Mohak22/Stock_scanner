# -*- coding: utf-8 -*-
"""
Created on Sun May 31 14:42:53 2026

@author: mohak
"""

from reports.email_sender import send_market_warning_email, send_no_sector_email, send_no_stock_email, send_stock_report_email 

def send_final_email(
    final_result: dict
):

    market_status = (
        final_result["market_status"]
    )

    sector_dataframe = (
        final_result["sector_dataframe"]
    )

    recommendations = (
        final_result["recommendations"]
    )

    if market_status == "PANIC":

        send_market_warning_email()

    elif sector_dataframe.empty:

        send_no_sector_email()

    elif recommendations.empty:

        send_no_stock_email()

    else:

        send_stock_report_email(
            recommendations
        )