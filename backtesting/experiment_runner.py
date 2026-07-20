# -*- coding: utf-8 -*-
"""
Created on Mon Jul 20 10:43:35 2026

@author: mohak
"""

from time import perf_counter

from backtesting.experiment import (
    Experiment
)
from backtesting.experiment_result import (
    ExperimentResult
)


class ExperimentRunner:

    def __init__(
        self,
        strategy_runner,
        recommendation_repository,
        analysis_engine,
        metrics_calculator
    ):

        self.strategy_runner = strategy_runner

        self.recommendation_repository = (
            recommendation_repository
        )

        self.analysis_engine = (
            analysis_engine
        )

        self.metrics_calculator = (
            metrics_calculator
        )

    def run(
        self,
        experiment: Experiment
    ) -> ExperimentResult:

        start_time = perf_counter()

        recommendations = (
            self.strategy_runner.run(
                experiment
            )
        )

        self.recommendation_repository.save(

            experiment=experiment,

            recommendations=recommendations

        )

        analysis = (
            self.analysis_engine.run(
                experiment=experiment
            )
        )

        metrics = (
            self.metrics_calculator.calculate(
                analysis
            )
        )

        execution_time = (
            perf_counter()
            - start_time
        )

        return ExperimentResult(

            experiment=experiment,

            metrics=metrics,

            execution_time=execution_time,

            recommendation_count=len(
                recommendations
            )
        )