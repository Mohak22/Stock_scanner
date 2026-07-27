# -*- coding: utf-8 -*-
"""
Created on Mon Jul 27 13:40:03 2026

@author: mohak
"""

# -*- coding: utf-8 -*-
"""
Strategy 2 hyperparameter tuning runner.

Runs selected Strategy 2 experiments in parallel
using ProcessPoolExecutor.
"""

from concurrent.futures import (
    ProcessPoolExecutor,
    as_completed
)

from datetime import date
from time import perf_counter

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

from strategies.strategy2.hyperparameter_tuning import (
    generate_strategy2_experiments
)


STRATEGY_NAME = "strategy2"


# =========================================================
# EXPERIMENT PERIOD
# =========================================================

START_DATE = date(
    2025,
    7,
    1
)

END_DATE = date(
    2026,
    6,
    30
)


# =========================================================
# EXPERIMENTS TO RUN
#
# 003 is already completed.
# First compare final Delivery/Volume weighting.
# =========================================================

EXPERIMENT_NUMBERS = [
    1,
    2,
    4,
    5
]


# =========================================================
# PARALLELISM
# =========================================================

MAX_WORKERS = 4


def run_single_experiment(
    experiment_number: int,
    experiment_id: str,
    config
) -> dict:

    """
    Run one Strategy 2 experiment.

    Everything is created inside the worker process
    so that experiments remain independent.
    """

    print(
        "\n=========================================="
    )

    print(
        f"STARTING: {experiment_id}"
    )

    print(
        f"Delivery / Volume: "
        f"{config.delivery_weight} / "
        f"{config.volume_weight}"
    )

    print(
        "=========================================="
    )

    # =====================================================
    # STRATEGY
    # =====================================================

    strategy = Strategy2(
        config=config
    )

    # =====================================================
    # EXPERIMENT
    # =====================================================

    experiment = Experiment(

        experiment_id=experiment_id,

        strategy=strategy,

        config=config,

        start_date=START_DATE,

        end_date=END_DATE

    )

    # =====================================================
    # EXPERIMENT MANAGER
    # =====================================================

    experiment_manager = (
        ExperimentManager(
            strategy_name=STRATEGY_NAME
        )
    )

    experiment_directory = (
        experiment_manager
        .get_experiment_directory(
            experiment
        )
    )

    metrics_file = (

        experiment_directory
        / "metrics.json"

    )

    # =====================================================
    # SKIP COMPLETED EXPERIMENT
    # =====================================================

    if metrics_file.exists():

        print(
            f"\n{experiment_id} already completed. "
            f"Skipping."
        )

        return {

            "experiment_number":
                experiment_number,

            "experiment_id":
                experiment_id,

            "status":
                "SKIPPED",

            "execution_time":
                0.0

        }

    # =====================================================
    # CREATE / RESTORE EXPERIMENT DIRECTORY
    # =====================================================

    if not experiment_directory.exists():

        experiment_directory = (
            experiment_manager
            .create_experiment(
                experiment
            )
        )

    else:

        experiment_manager.save_configuration(
            experiment
        )

    # =====================================================
    # COMPONENTS
    #
    # Created independently inside each worker.
    # =====================================================

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

    # =====================================================
    # EXPERIMENT RUNNER
    # =====================================================

    experiment_runner = (
        ExperimentRunner(

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
    )

    # =====================================================
    # RUN
    # =====================================================

    result = (
        experiment_runner.run(
            experiment=experiment
        )
    )

    print(
        f"\nCOMPLETED: "
        f"{experiment_id}"
    )

    print(
        f"Recommendations: "
        f"{result.recommendation_count}"
    )

    print(
        f"Execution time: "
        f"{result.execution_time:.2f} seconds"
    )

    return {

        "experiment_number":
            experiment_number,

        "experiment_id":
            experiment_id,

        "status":
            "COMPLETED",

        "execution_time":
            result.execution_time,

        "recommendation_count":
            result.recommendation_count,

        "metrics":
            result.metrics

    }


def main():

    tuning_start_time = perf_counter()

    # =====================================================
    # LOAD EXPERIMENT DEFINITIONS
    # =====================================================

    experiment_definitions = (
        generate_strategy2_experiments()
    )

    total_experiments = len(
        experiment_definitions
    )

    # =====================================================
    # VALIDATE EXPERIMENT NUMBERS
    # =====================================================

    for experiment_number in (
        EXPERIMENT_NUMBERS
    ):

        if not (
            1
            <= experiment_number
            <= total_experiments
        ):

            raise ValueError(

                f"Invalid experiment number: "
                f"{experiment_number}. "
                f"Available: "
                f"1 -> {total_experiments}"

            )

    # =====================================================
    # PREPARE SELECTED EXPERIMENTS
    # =====================================================

    selected_experiments = []

    for experiment_number in (
        EXPERIMENT_NUMBERS
    ):

        experiment_id, config = (

            experiment_definitions[
                experiment_number - 1
            ]

        )

        selected_experiments.append(

            (
                experiment_number,
                experiment_id,
                config
            )

        )

    print(
        "\n=========================================="
    )

    print(
        "STRATEGY 2 PARALLEL TUNING"
    )

    print(
        "=========================================="
    )

    print(
        f"Period: "
        f"{START_DATE} -> {END_DATE}"
    )

    print(
        f"Experiments: "
        f"{EXPERIMENT_NUMBERS}"
    )

    print(
        f"Workers: "
        f"{MAX_WORKERS}"
    )

    # =====================================================
    # RUN IN PARALLEL
    # =====================================================

    results = []

    with ProcessPoolExecutor(

        max_workers=MAX_WORKERS

    ) as executor:

        future_to_experiment = {}

        for (

            experiment_number,
            experiment_id,
            config

        ) in selected_experiments:

            future = executor.submit(

                run_single_experiment,

                experiment_number,

                experiment_id,

                config

            )

            future_to_experiment[
                future
            ] = experiment_id

        # =================================================
        # COLLECT RESULTS AS THEY FINISH
        # =================================================

        for future in as_completed(
            future_to_experiment
        ):

            experiment_id = (
                future_to_experiment[
                    future
                ]
            )

            try:

                result = future.result()

                results.append(
                    result
                )

            except Exception as error:

                print(
                    "\n=========================================="
                )

                print(
                    f"FAILED: "
                    f"{experiment_id}"
                )

                print(
                    f"Error: "
                    f"{error}"
                )

                print(
                    "=========================================="
                )

                results.append(
                    {

                        "experiment_id":
                            experiment_id,

                        "status":
                            "FAILED",

                        "error":
                            str(error)

                    }
                )

    # =====================================================
    # FINAL SUMMARY
    # =====================================================

    total_time = (

        perf_counter()
        - tuning_start_time

    )

    print(
        "\n\n=========================================="
    )

    print(
        "PARALLEL TUNING COMPLETED"
    )

    print(
        "=========================================="
    )

    for result in sorted(

        results,

        key=lambda item: (
            item.get(
                "experiment_number",
                999
            )
        )

    ):

        print(
            f"{result['experiment_id']}: "
            f"{result['status']}"
        )

        if (
            result["status"]
            == "COMPLETED"
        ):

            print(
                f"    Runtime: "
                f"{result['execution_time']:.2f}s"
            )

            print(
                f"    Recommendations: "
                f"{result['recommendation_count']}"
            )

    print(
        "\nTotal wall-clock time: "
        f"{total_time:.2f} seconds"
    )


if __name__ == "__main__":

    main()