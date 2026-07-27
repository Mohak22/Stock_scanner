# -*- coding: utf-8 -*-
"""
Created on Mon Jul 20 11:09:54 2026

@author: mohak
"""

import pandas as pd


class StrategyRunner:

    def __init__(
        self,
        strategy
    ):

        self.strategy = strategy

    def run(
        self,
        experiment,
        history: pd.DataFrame,
        recommendation_dates: list
    ) -> pd.DataFrame:
        """
        Run the strategy for every recommendation date
        in the experiment.
    
        The complete historical dataset may contain future
        data required later for return analysis.
    
        Before the strategy is called, history is sliced so
        that the strategy can only see data available up to
        the current recommendation date.
        """
    
        recommendations = []
    
        total_dates = len(
            recommendation_dates
        )
    
        print(
            f"\nRecommendation dates: "
            f"{total_dates}"
        )
    
        history = history.copy()
    
        history["TIMESTAMP"] = pd.to_datetime(
            history["TIMESTAMP"]
        )
    
        # ==========================================
        # RUN EACH RECOMMENDATION DATE
        # ==========================================
    
        for index, recommendation_date in enumerate(
            recommendation_dates,
            start=1
        ):
    
            recommendation_timestamp = pd.Timestamp(
                recommendation_date
            ).normalize()
    
            print(
                f"[{index}/{total_dates}] "
                f"Running: "
                f"{recommendation_timestamp.date()}"
            )
    
            # ======================================
            # PREVENT LOOK-AHEAD
            # ======================================
    
            available_history = history[
    
                history["TIMESTAMP"]
                <= recommendation_timestamp
    
            ].copy()
    
            if available_history.empty:
    
                continue
    
            # ======================================
            # KEEP ONLY REQUIRED HISTORY WINDOW
            # ======================================
    
            available_dates = (
    
                available_history[
                    "TIMESTAMP"
                ]
    
                .drop_duplicates()
    
                .sort_values()
    
            )
    
            required_dates = (
    
                available_dates
                .tail(
                    experiment.config.history_window
                )
    
            )
    
            strategy_history = (
    
                available_history[
    
                    available_history[
                        "TIMESTAMP"
                    ].isin(
                        required_dates
                    )
    
                ]
    
                .copy()
    
            )
    
            # ======================================
            # RUN STRATEGY
            # ======================================
    
            daily_recommendations = (
                self.strategy.run(
    
                    recommendation_date=(
                        recommendation_timestamp.date()
                    ),
    
                    history=strategy_history
    
                )
            )
    
            # ======================================
            # COLLECT RECOMMENDATIONS
            # ======================================
    
            if (
                daily_recommendations is not None
                and
                not daily_recommendations.empty
            ):
    
                recommendations.append(
                    daily_recommendations
                )
    
        # ==========================================
        # NO RECOMMENDATIONS
        # ==========================================
    
        if not recommendations:
    
            return pd.DataFrame()
    
        # ==========================================
        # COMBINE ALL DATES
        # ==========================================
    
        return pd.concat(
    
            recommendations,
    
            ignore_index=True
    
        )