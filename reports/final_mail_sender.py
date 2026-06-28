# -*- coding: utf-8 -*-
"""
Created on Sun May 31 14:42:53 2026

@author: mohak
"""

from reports.email_sender import (
    send_no_stock_email,
    send_stock_report_email,
    send_strategy_output_email
)

from reports.recommendation_workbook import (
    generate_recommendation_workbook
)


def send_final_email(
    final_result: dict
) -> None:

    recommendations = (
        final_result["recommendations"]
    )

    workbook_result = (
        generate_recommendation_workbook()
    )

    workbook_path = (
        workbook_result["workbook_path"]
    )

    final_recommendations_found = (
        workbook_result[
            "final_recommendations_found"
        ]
    )

    strategy_outputs_found = (
        workbook_result[
            "strategy_outputs_found"
        ]
    )

    # =============================================
    # CASE 1
    # FINAL RECOMMENDATIONS AVAILABLE
    # =============================================

    if final_recommendations_found:

        send_stock_report_email(

            recommendations=
                recommendations,

            workbook_path=
                workbook_path
        )

        return

    # =============================================
    # CASE 2
    # STRATEGY OUTPUTS AVAILABLE
    # BUT NO FINAL RECOMMENDATION
    # =============================================

    if strategy_outputs_found:

        send_strategy_output_email(

            workbook_path=
                workbook_path
        )

        return

    # =============================================
    # CASE 3
    # NOTHING GENERATED TODAY
    # =============================================

    send_no_stock_email()