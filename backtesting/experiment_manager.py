# -*- coding: utf-8 -*-
"""
Created on Mon Jul 20 11:00:44 2026

@author: mohak
"""

import json

from dataclasses import asdict
from pathlib import Path

from paths.config import (
    BACKTEST_STRATEGIES_FOLDER
)


class ExperimentManager:

    def __init__(
        self,
        strategy_name: str
    ):

        self.strategy_directory = (
            BACKTEST_STRATEGIES_FOLDER
            / strategy_name
        )

        self.strategy_directory.mkdir(
            parents=True,
            exist_ok=True
        )

    def create_experiment(
        self,
        experiment
    ) -> Path:

        experiment_directory = (
            self.strategy_directory
            / experiment.experiment_id
        )

        experiment_directory.mkdir(
            parents=True,
            exist_ok=False
        )

        self.save_configuration(
            experiment
        )

        return experiment_directory

    def save_configuration(
        self,
        experiment
    ):

        configuration_file = (
            self.strategy_directory
            / experiment.experiment_id
            / "config.json"
        )

        with open(
            configuration_file,
            "w"
        ) as file:

            json.dump(

                asdict(
                    experiment.config
                ),

                file,

                indent=4,

                default=str

            )

    def get_experiment_directory(
        self,
        experiment
    ) -> Path:

        return (
            self.strategy_directory
            / experiment.experiment_id
        )