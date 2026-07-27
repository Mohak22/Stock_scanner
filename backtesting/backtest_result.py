# -*- coding: utf-8 -*-
"""
Created on ...

@author: mohak
"""

from dataclasses import dataclass

from backtesting.backtest_experiment import (
    Experiment
)


@dataclass
class ExperimentResult:

    experiment: Experiment

    metrics: dict

    execution_time: float

    recommendation_count: int