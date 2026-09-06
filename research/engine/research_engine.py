# -*- coding: utf-8 -*-
"""
Created on Fri Sep  4 12:03:36 2026

@author: mohak
"""

"""
Research engine for strategy experimentation.
"""

import pandas as pd

from research.engine.condition_engine import apply_conditions
from research.engine.return_engine import calculate_forward_returns


def build_research_diagnostics(
    dataframe: pd.DataFrame,
    signal_data: pd.DataFrame,
    horizons: list[int],
) -> dict:
    """
    Build factual diagnostics and performance metrics for a research split.

    Supports:
        - Stock forward returns
        - Market forward returns
        - Excess returns versus market
        - Signal sample diagnostics
        - Stock coverage diagnostics
        - Outcome quality diagnostics
        - Research warnings
    """

    total_rows = len(dataframe)
    signal_count = len(signal_data)

    signal_rate = (
        round(signal_count / total_rows * 100, 2)
        if total_rows
        else 0.0
    )

    # ---------------------------------------------------------
    # Signal coverage
    # ---------------------------------------------------------

    if signal_count and "SYMBOL" in signal_data.columns:
        stocks_with_signals = int(
            signal_data["SYMBOL"].nunique()
        )
    else:
        stocks_with_signals = 0

    if signal_count and "TIMESTAMP" in signal_data.columns:
        signal_start = signal_data["TIMESTAMP"].min()
        signal_end = signal_data["TIMESTAMP"].max()

        signal_date_range = {
            "start": signal_start.strftime("%Y-%m-%d"),
            "end": signal_end.strftime("%Y-%m-%d"),
        }
    else:
        signal_date_range = {
            "start": None,
            "end": None,
        }

    # ---------------------------------------------------------
    # Sample quality
    # ---------------------------------------------------------

    if signal_count < 10:
        sample_classification = "VERY_LOW"
    elif signal_count < 30:
        sample_classification = "LOW"
    else:
        sample_classification = "ADEQUATE"

    # ---------------------------------------------------------
    # Stock coverage
    # ---------------------------------------------------------

    if stocks_with_signals == 0:
        stock_classification = "NONE"
    elif stocks_with_signals < 3:
        stock_classification = "LOW"
    else:
        stock_classification = "ADEQUATE"

    # ---------------------------------------------------------
    # Warnings
    # ---------------------------------------------------------

    warnings = []

    if signal_count == 0:
        warnings.append("NO_SIGNALS")
    elif signal_count < 10:
        warnings.append("VERY_LOW_SIGNAL_COUNT")
    elif signal_count < 30:
        warnings.append("LOW_SIGNAL_COUNT")

    if stocks_with_signals == 0:
        warnings.append("NO_STOCK_COVERAGE")
    elif stocks_with_signals < 3:
        warnings.append("LOW_STOCK_COVERAGE")

    # ---------------------------------------------------------
    # Performance + outcome quality
    # ---------------------------------------------------------

    performance = {}
    outcome_quality = {}

    for horizon in horizons:

        horizon = int(horizon)

        stock_column = f"RETURN_T{horizon}"
        market_column = f"MARKET_RETURN_T{horizon}"
        excess_column = f"EXCESS_RETURN_T{horizon}"

        # -----------------------------------------------------
        # Validate stock return column
        # -----------------------------------------------------

        if stock_column not in signal_data.columns:
            raise ValueError(
                f"Expected return column "
                f"'{stock_column}' was not found."
            )

        stock_returns = signal_data[
            stock_column
        ].dropna()

        observations = len(stock_returns)

        # -----------------------------------------------------
        # No stock outcomes
        # -----------------------------------------------------

        if observations == 0:

            performance[f"T+{horizon}"] = {
                "observations": 0,

                "average_return": None,
                "median_return": None,
                "positive_return_pct": None,
                "negative_return_pct": None,
                "best_return": None,
                "worst_return": None,

                "market_observations": 0,
                "average_market_return": None,
                "median_market_return": None,

                "excess_observations": 0,
                "average_excess_return": None,
                "median_excess_return": None,
                "outperformed_market_pct": None,
            }

            outcome_quality[f"T+{horizon}"] = {
                "valid_observations": 0,
                "classification": "NONE",
            }

            warnings.append(
                f"NO_VALID_OUTCOMES_T{horizon}"
            )

            continue

        # -----------------------------------------------------
        # Stock performance
        # -----------------------------------------------------

        performance_data = {
            "observations": observations,

            "average_return": round(
                float(stock_returns.mean()),
                4,
            ),

            "median_return": round(
                float(stock_returns.median()),
                4,
            ),

            "positive_return_pct": round(
                float(
                    (stock_returns > 0).mean() * 100
                ),
                2,
            ),

            "negative_return_pct": round(
                float(
                    (stock_returns < 0).mean() * 100
                ),
                2,
            ),

            "best_return": round(
                float(stock_returns.max()),
                4,
            ),

            "worst_return": round(
                float(stock_returns.min()),
                4,
            ),
        }

        # -----------------------------------------------------
        # Market-relative performance
        # -----------------------------------------------------

        if (
            market_column in signal_data.columns
            and excess_column in signal_data.columns
        ):

            relative_data = signal_data[
                [
                    market_column,
                    excess_column,
                ]
            ].dropna()

            market_returns = relative_data[
                market_column
            ]

            excess_returns = relative_data[
                excess_column
            ]

            market_observations = len(
                market_returns
            )

            excess_observations = len(
                excess_returns
            )

            if market_observations:
                average_market_return = round(
                    float(market_returns.mean()),
                    4,
                )

                median_market_return = round(
                    float(market_returns.median()),
                    4,
                )
            else:
                average_market_return = None
                median_market_return = None

            if excess_observations:

                average_excess_return = round(
                    float(excess_returns.mean()),
                    4,
                )

                median_excess_return = round(
                    float(excess_returns.median()),
                    4,
                )

                outperformed_market_pct = round(
                    float(
                        (excess_returns > 0).mean()
                        * 100
                    ),
                    2,
                )

            else:
                average_excess_return = None
                median_excess_return = None
                outperformed_market_pct = None

        else:

            market_observations = 0
            average_market_return = None
            median_market_return = None

            excess_observations = 0
            average_excess_return = None
            median_excess_return = None
            outperformed_market_pct = None

        # -----------------------------------------------------
        # Final horizon performance
        # -----------------------------------------------------

        performance[f"T+{horizon}"] = {
            **performance_data,

            "market_observations": market_observations,
            "average_market_return": average_market_return,
            "median_market_return": median_market_return,

            "excess_observations": excess_observations,
            "average_excess_return": average_excess_return,
            "median_excess_return": median_excess_return,
            "outperformed_market_pct": outperformed_market_pct,
        }

        # -----------------------------------------------------
        # Outcome quality
        # -----------------------------------------------------

        if observations < 10:
            outcome_classification = "LOW"

            warnings.append(
                f"LOW_VALID_OUTCOMES_T{horizon}"
            )
        else:
            outcome_classification = "ADEQUATE"

        outcome_quality[f"T+{horizon}"] = {
            "valid_observations": observations,
            "classification": outcome_classification,
        }

    # ---------------------------------------------------------
    # Final diagnostics
    # ---------------------------------------------------------

    diagnostics = {
        "sample_quality": {
            "signal_count": signal_count,
            "classification": sample_classification,
        },

        "stock_coverage": {
            "stocks_with_signals": stocks_with_signals,
            "classification": stock_classification,
        },

        "outcome_quality": outcome_quality,
    }

    return {
        "summary": {
            "total_rows": total_rows,
            "signal_count": signal_count,
            "signal_rate": signal_rate,
            "stocks_with_signals": stocks_with_signals,
            "signal_date_range": signal_date_range,
        },

        "performance": performance,

        "diagnostics": diagnostics,

        "warnings": sorted(
            set(warnings)
        ),
    }


def run_research(
    dataframe: pd.DataFrame,
    features: list,
    conditions: list,
    horizons: list[int],
) -> dict:
    """
    Run signal research and return performance plus diagnostics.
    """

    if not horizons:
        raise ValueError(
            "At least one evaluation horizon is required."
        )

    if any(
        int(horizon) <= 0
        for horizon in horizons
    ):
        raise ValueError(
            "Evaluation horizons must be positive integers."
        )

    data = dataframe.copy()

    # ---------------------------------------------------------
    # Generate strategy signals
    # ---------------------------------------------------------

    data["SIGNAL"] = apply_conditions(
        dataframe=data,
        conditions=conditions,
    )

    # ---------------------------------------------------------
    # Calculate stock forward returns
    # ---------------------------------------------------------

    data = calculate_forward_returns(
        dataframe=data,
        horizons=horizons,
    )

    # ---------------------------------------------------------
    # Keep only signal rows
    # ---------------------------------------------------------

    signal_data = data[
        data["SIGNAL"]
    ].copy()

    # ---------------------------------------------------------
    # Build complete research result
    # ---------------------------------------------------------

    result = build_research_diagnostics(
        dataframe=data,
        signal_data=signal_data,
        horizons=horizons,
    )

    return {
        "summary": result["summary"],
        "performance": result["performance"],
        "diagnostics": result["diagnostics"],
        "warnings": result["warnings"],
        "signals": signal_data,
    }