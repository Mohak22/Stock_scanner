# -*- coding: utf-8 -*-
"""
Created on Mon Jul 20 11:09:54 2026

@author: mohak
"""

from collections import defaultdict

import pandas as pd


class StrategyRunner:

    def __init__(
        self,
        strategy
    ):

        self.strategy = strategy

    def run(
        self,
        experiment: object,
        historical_data: dict[str, pd.DataFrame]
    ) -> pd.DataFrame:

        recommendations = []

        for stock_symbol, stock_data in historical_data.items():

            stock_recommendations = (
                self.strategy.run_backtest(
                    stock_symbol=stock_symbol,
                    stock_data=stock_data,
                    config=experiment.config,
                    start_date=experiment.start_date,
                    end_date=experiment.end_date
                )
            )

            if (
                stock_recommendations
                is not None
                and
                not stock_recommendations.empty
            ):

                recommendations.append(
                    stock_recommendations
                )

        if not recommendations:

            return pd.DataFrame()

        return pd.concat(

            recommendations,

            ignore_index=True

        )