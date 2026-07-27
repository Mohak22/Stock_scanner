# -*- coding: utf-8 -*-
"""
Created on Mon Jul 20 10:50:13 2026

@author: mohak
"""

from pathlib import Path

import pandas as pd

from config.paths import (
    BACKTEST_STRATEGIES_FOLDER
)


class RecommendationRepository:

    def __init__(
        self,
        strategy_name: str
    ):

        self.strategy_directory = (
            BACKTEST_STRATEGIES_FOLDER
            / strategy_name
        )

    def save(
        self,
        experiment,
        recommendations: pd.DataFrame
    ) -> Path:

        experiment_directory = (
            self.strategy_directory
            / experiment.experiment_id
        )

        experiment_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        recommendation_file = (
            experiment_directory
            / "recommendations.csv"
        )

        recommendations.to_csv(
            recommendation_file,
            index=False
        )

        return recommendation_file

    def load(
        self,
        experiment
    ) -> pd.DataFrame:

        recommendation_file = (
            self.strategy_directory
            / experiment.experiment_id
            / "recommendations.csv"
        )

        return pd.read_csv(
            recommendation_file
        )