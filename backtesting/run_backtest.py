# -*- coding: utf-8 -*-
"""
Created on Sun Jul 26 14:35:26 2026

@author: mohak
"""

from datetime import date

from backtesting.backtest_experiment import (
    Experiment
)

from backtesting.experiment_manager import (
    ExperimentManager
)

from backtesting.experiment_runner import (
    ExperimentRunner
)

from backtesting.historical_data_repository import (
    HistoricalDataRepository
)

from backtesting.trading_calendar import (
    TradingCalendar
)

from backtesting.strategy_runner import (
    StrategyRunner
)

from backtesting.recommendation_repository import (
    RecommendationRepository
)

from backtesting.nifty_data_repository import (
    NiftyDataRepository
)

from strategies.strategy2.accumulation import (
    Strategy2
)

from strategies.strategy2.strategy2_config import (
    Strategy2Config
)


STRATEGY_NAME = "strategy2"


def main():

    # ==========================================
    # CONFIG
    # ==========================================

    config = Strategy2Config()

    # ==========================================
    # STRATEGY
    # ==========================================

    strategy = Strategy2(
        config=config
    )

    # ==========================================
    # EXPERIMENT
    # ==========================================

    experiment = Experiment(

        experiment_id="experiment_004",

        strategy=strategy,

        config=config,

        start_date=date(
            2026,
            7,
            1
        ),

        end_date=date(
            2026,
            7,
            1
        )

    )

    # ==========================================
    # CREATE EXPERIMENT DIRECTORY
    # ==========================================

    experiment_manager = ExperimentManager(
        strategy_name=STRATEGY_NAME
    )

    experiment_directory = (
        experiment_manager.create_experiment(
            experiment
        )
    )

    print(
        f"\nExperiment directory: "
        f"{experiment_directory}"
    )

    # ==========================================
    # COMPONENTS
    # ==========================================

    historical_data_repository = (
        HistoricalDataRepository()
    )

    trading_calendar = (
        TradingCalendar()
    )

    strategy_runner = (
        StrategyRunner(
            strategy=strategy
        )
    )

    recommendation_repository = (
        RecommendationRepository(
            strategy_name=STRATEGY_NAME
        )
    )

    nifty_data_repository = (
        NiftyDataRepository()
    )

    # ==========================================
    # EXPERIMENT RUNNER
    # ==========================================

    experiment_runner = ExperimentRunner(

        historical_data_repository=(
            historical_data_repository
        ),

        trading_calendar=(
            trading_calendar
        ),

        strategy_runner=(
            strategy_runner
        ),

        recommendation_repository=(
            recommendation_repository
        ),

        nifty_data_repository=(
            nifty_data_repository
        )

    )

    # ==========================================
    # RUN
    # ==========================================

    print(
        "\nStarting backtest..."
    )

    result = experiment_runner.run(
        experiment=experiment
    )

    # ==========================================
    # RESULT
    # ==========================================

    print(
        "\nBacktest completed."
    )

    print(
        f"Experiment: "
        f"{result.experiment.experiment_id}"
    )

    print(
        f"Recommendations: "
        f"{result.recommendation_count}"
    )

    print(
        f"Execution time: "
        f"{result.execution_time:.2f} seconds"
    )


if __name__ == "__main__":

    main()