# -*- coding: utf-8 -*-
"""
Created on Mon Jul 27 17:28:27 2026

@author: mohak
"""

"""
Compare completed Strategy 2 backtesting experiments.
"""

import json

import pandas as pd

from config.paths import (
    BACKTEST_STRATEGIES_FOLDER
)


STRATEGY_NAME = "strategy2"

OUTPUT_FILE_NAME = (
    "experiment_comparison.csv"
)


def load_experiment_metrics() -> pd.DataFrame:

    strategy_directory = (
        BACKTEST_STRATEGIES_FOLDER
        / STRATEGY_NAME
    )

    if not strategy_directory.exists():

        raise FileNotFoundError(
            f"Strategy directory not found: "
            f"{strategy_directory}"
        )

    experiment_rows = []

    experiment_directories = sorted(
        strategy_directory.glob(
            "s2_*"
        )
    )

    for experiment_directory in (
        experiment_directories
    ):

        if not experiment_directory.is_dir():

            continue

        metrics_file = (
            experiment_directory
            / "metrics.json"
        )

        config_file = (
            experiment_directory
            / "config.json"
        )

        # Ignore incomplete experiments
        if not metrics_file.exists():

            print(
                f"Skipping incomplete experiment: "
                f"{experiment_directory.name}"
            )

            continue

        # ==========================================
        # LOAD METRICS
        # ==========================================

        with open(
            metrics_file,
            "r",
            encoding="utf-8"
        ) as file:

            metrics = json.load(
                file
            )

        # ==========================================
        # LOAD CONFIG
        # ==========================================

        config = {}

        if config_file.exists():

            with open(
                config_file,
                "r",
                encoding="utf-8"
            ) as file:

                config = json.load(
                    file
                )

        # ==========================================
        # BUILD COMPARISON ROW
        # ==========================================

        row = {

            "experiment_id":
                experiment_directory.name,

            # --------------------------------------
            # CONFIG
            # --------------------------------------

            "delivery_weight":
                config.get(
                    "delivery_weight"
                ),

            "volume_weight":
                config.get(
                    "volume_weight"
                ),

            "delivery_recent_weight":
                config.get(
                    "delivery_recent_weight"
                ),

            "delivery_medium_weight":
                config.get(
                    "delivery_medium_weight"
                ),

            "volume_recent_weight":
                config.get(
                    "volume_recent_weight"
                ),

            "volume_medium_weight":
                config.get(
                    "volume_medium_weight"
                ),

            "top_n":
                config.get(
                    "top_n"
                ),

            # --------------------------------------
            # RECOMMENDATIONS
            # --------------------------------------

            "recommendation_count":
                metrics.get(
                    "recommendation_count"
                ),

            # --------------------------------------
            # BTST
            # --------------------------------------

            "btst_mean":
                metrics.get(
                    "btst_mean_return_pct"
                ),

            "btst_median":
                metrics.get(
                    "btst_median_return_pct"
                ),

            "btst_positive_pct":
                metrics.get(
                    "btst_positive_pct"
                ),

            "btst_mean_outperformance":
                metrics.get(
                    "btst_mean_outperformance_pct"
                ),

            "btst_outperformance_positive_pct":
                metrics.get(
                    "btst_outperformance_positive_pct"
                ),

            # --------------------------------------
            # 7 DAY
            # --------------------------------------

            "7d_mean":
                metrics.get(
                    "7d_mean_return_pct"
                ),

            "7d_median":
                metrics.get(
                    "7d_median_return_pct"
                ),

            "7d_positive_pct":
                metrics.get(
                    "7d_positive_pct"
                ),

            "7d_mean_outperformance":
                metrics.get(
                    "7d_mean_outperformance_pct"
                ),

            "7d_outperformance_positive_pct":
                metrics.get(
                    "7d_outperformance_positive_pct"
                ),

            # --------------------------------------
            # 14 DAY
            # --------------------------------------

            "14d_valid_count":
                metrics.get(
                    "14d_valid_count"
                ),

            "14d_mean":
                metrics.get(
                    "14d_mean_return_pct"
                ),

            "14d_median":
                metrics.get(
                    "14d_median_return_pct"
                ),

            "14d_positive_pct":
                metrics.get(
                    "14d_positive_pct"
                ),

            "14d_mean_outperformance":
                metrics.get(
                    "14d_mean_outperformance_pct"
                ),

            "14d_outperformance_positive_pct":
                metrics.get(
                    "14d_outperformance_positive_pct"
                ),

            # --------------------------------------
            # RANGE
            # --------------------------------------

            "mean_highest_return":
                metrics.get(
                    "mean_highest_return_pct"
                ),

            "median_highest_return":
                metrics.get(
                    "median_highest_return_pct"
                ),

            "mean_lowest_return":
                metrics.get(
                    "mean_lowest_return_pct"
                ),

            "median_lowest_return":
                metrics.get(
                    "median_lowest_return_pct"
                )

        }

        experiment_rows.append(
            row
        )

    if not experiment_rows:

        raise ValueError(
            "No completed Strategy 2 "
            "experiments found."
        )

    comparison = pd.DataFrame(
        experiment_rows
    )

    comparison = (
        comparison
        .sort_values(
            "experiment_id"
        )
        .reset_index(
            drop=True
        )
    )

    return comparison


def save_comparison(
    comparison: pd.DataFrame
) -> None:

    output_directory = (
        BACKTEST_STRATEGIES_FOLDER
        / STRATEGY_NAME
    )

    output_file = (
        output_directory
        / OUTPUT_FILE_NAME
    )

    comparison.to_csv(
        output_file,
        index=False
    )

    print(
        f"\nComparison saved:"
        f"\n{output_file}"
    )


def print_comparison(
    comparison: pd.DataFrame
) -> None:

    # Smaller table for terminal inspection.
    # Full metrics remain in the CSV.

    display_columns = [

        "experiment_id",

        "delivery_weight",
        "volume_weight",

        "recommendation_count",

        "btst_mean",
        "btst_median",
        "btst_positive_pct",
        "btst_mean_outperformance",

        "7d_mean",
        "7d_median",
        "7d_positive_pct",
        "7d_mean_outperformance",

        "14d_mean",
        "14d_median",
        "14d_positive_pct",
        "14d_mean_outperformance",

        "mean_highest_return",
        "mean_lowest_return"

    ]

    print(
        "\n=========================================="
    )

    print(
        "STRATEGY 2 EXPERIMENT COMPARISON"
    )

    print(
        "==========================================\n"
    )

    print(

        comparison[
            display_columns
        ].to_string(

            index=False

        )

    )


def main():

    comparison = (
        load_experiment_metrics()
    )

    print_comparison(
        comparison
    )

    save_comparison(
        comparison
    )


if __name__ == "__main__":

    main()