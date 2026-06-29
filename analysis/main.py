# -*- coding: utf-8 -*-
"""
Created on Mon Jun  8 13:47:34 2026

@author: mohak
"""

from datetime import date, timedelta

from config.paths import FINAL_RECOMMENDATIONS_FOLDER, STRATEGIES_FOLDER
from loaders.recommendation_loader import load_recommendations
from calculators.return_calculator import calculate_returns
from storage.analysis_saver import save_analysis
from reports.generate_excel_report import generate_excel_report
from reports.analysis_email_sender import send_analysis_report, send_no_analysis_report
from loaders.strategy_discovery import get_strategy_folders

def main():

    target_date = (
        date.today()
        - timedelta(days=14)
    )

    final_df = load_recommendations(
        FINAL_RECOMMENDATIONS_FOLDER,
        "final_recommendations",
        target_date
    )

    strategy_folders = (
        get_strategy_folders(
            STRATEGIES_FOLDER
        )
    )

    strategy_dfs = {}

    for strategy_folder in strategy_folders:

        strategy_name = (
            strategy_folder.name
        )

        strategy_df = (
            load_recommendations(
                strategy_folder,
                strategy_name,
                target_date
            )
        )

        strategy_dfs[
            strategy_name
        ] = strategy_df

    all_strategies_empty = all(
        strategy_df.empty
        for strategy_df
        in strategy_dfs.values()
    )

    if (final_df.empty and all_strategies_empty):
        send_no_analysis_report()

        return

    final_analysis_df = (
        calculate_returns(final_df)
    )

    strategy_analysis_dfs = {}

    for (strategy_name, strategy_df) in strategy_dfs.items():
        
        strategy_analysis_dfs[
            strategy_name
        ] = calculate_returns(
            strategy_df
        )

    save_analysis(
        final_analysis_df,
        "final_recommendations"
    )

    for (strategy_name, analysis_df) in strategy_analysis_dfs.items():

        save_analysis(analysis_df, strategy_name)

    report_path = (
        generate_excel_report(
            final_analysis_df,
            strategy_analysis_dfs
        )
    )
    
    strategy_names = [
        strategy_name
        for (strategy_name, analysis_df) in strategy_analysis_dfs.items()
        if not analysis_df.empty
    ]

    send_analysis_report(
        report_path,
        strategy_names
    )


if __name__ == "__main__":
    main()