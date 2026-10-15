# -*- coding: utf-8 -*-
"""
Created on Thu Oct 15 22:03:46 2026

@author: mohak
"""


"""Date-stratified random baseline for historical stock research."""

import numpy as np
import pandas as pd


def build_random_baseline(
    candidate_data: pd.DataFrame,
    signal_data: pd.DataFrame,
    horizons: list[int],
    permutations: int = 999,
    random_seed: int = 20261014,
) -> dict:
    """
    Compare selected signals with random eligible stock selections.

    For each date and horizon, preserve the number of actual signals
    with eligible outcomes. Sample candidate outcomes without
    replacement within that date.

    Metric: net excess return, in percentage points.
    The reported p-value is nominal; temporal dependence is not
    fully corrected by this procedure.
    """
    if permutations < 1:
        raise ValueError("permutations must be positive.")

    result = {
        "method": "date_stratified_random_selection",
        "metric": "NET_EXCESS_RETURN",
        "permutations_requested": int(permutations),
        "random_seed": int(random_seed),
        "interpretation": (
            "Compares selected stocks with random eligible stocks "
            "on the same dates while preserving the number of "
            "eligible signals per date. P-values are nominal and "
            "do not fully correct for overlapping outcomes, "
            "serial dependence, or multiple testing."
        ),
        "by_horizon": {},
    }

    if signal_data.empty:
        for horizon in sorted(set(horizons)):
            result["by_horizon"][f"T+{horizon}"] = {
                "status": "NO_SIGNALS",
                "observations": 0,
            }
        return result

    for horizon in sorted(set(int(h) for h in horizons)):
        suffix = f"T{horizon}"
        eligible_col = f"OUTCOME_ELIGIBLE_{suffix}"
        metric_col = f"NET_EXCESS_RETURN_{suffix}"

        required = {"TIMESTAMP", eligible_col, metric_col}

        if not required.issubset(signal_data.columns):
            raise ValueError(
                f"Signal data missing columns for {suffix}: "
                f"{sorted(required - set(signal_data.columns))}"
            )

        if not required.issubset(candidate_data.columns):
            raise ValueError(
                f"Candidate data missing columns for {suffix}: "
                f"{sorted(required - set(candidate_data.columns))}"
            )

        def prepare(frame):
            prepared = frame[
                ["TIMESTAMP", eligible_col, metric_col]
            ].copy()

            prepared["TIMESTAMP"] = (
                pd.to_datetime(
                    prepared["TIMESTAMP"],
                    errors="coerce",
                ).dt.normalize()
            )
            prepared[metric_col] = pd.to_numeric(
                prepared[metric_col],
                errors="coerce",
            )

            eligible = (
                prepared[eligible_col]
                .fillna(False)
                .astype(bool)
            )

            prepared = prepared.loc[
                eligible
                & prepared["TIMESTAMP"].notna()
                & prepared[metric_col].notna()
            ].copy()

            return prepared

        observed = prepare(signal_data)
        candidates = prepare(candidate_data)

        if observed.empty:
            result["by_horizon"][f"T+{horizon}"] = {
                "status": "NO_VALID_OUTCOMES",
                "observations": 0,
            }
            continue

        # Preserve the actual number of eligible outcomes per date.
        counts_by_date = (
            observed.groupby("TIMESTAMP", sort=True)
            .size()
        )

        candidate_values_by_date = {
            date: group[metric_col].to_numpy(dtype=float)
            for date, group in candidates.groupby(
                "TIMESTAMP",
                sort=True,
            )
        }

        daily_pools = []

        for date, count in counts_by_date.items():
            pool = candidate_values_by_date.get(
                date,
                np.array([], dtype=float),
            )

            if len(pool) < int(count):
                raise ValueError(
                    f"Random baseline has only {len(pool)} eligible "
                    f"candidates on {date.date()}, but the observed "
                    f"strategy has {int(count)} eligible outcomes."
                )

            daily_pools.append((pool, int(count)))

        observed_values = observed[metric_col].to_numpy(dtype=float)
        observed_mean = float(observed_values.mean())

        rng = np.random.default_rng(random_seed + horizon)
        null_means = np.empty(permutations, dtype=float)

        for iteration in range(permutations):
            sampled_returns = []

            for pool, count in daily_pools:
                selected = rng.choice(
                    pool,
                    size=count,
                    replace=False,
                )
                sampled_returns.extend(selected.tolist())

            null_means[iteration] = np.mean(sampled_returns)

        null_mean = float(null_means.mean())

        # One-sided test: is observed performance greater than random?
        p_value = float(
            (
                1 + np.count_nonzero(null_means >= observed_mean)
            )
            / (permutations + 1)
        )

        result["by_horizon"][f"T+{horizon}"] = {
            "status": (
                "LOW_SAMPLE"
                if len(observed_values) < 30
                else "OK"
            ),
            "observations": int(len(observed_values)),
            "dates_with_signals": int(len(counts_by_date)),
            "observed_mean_net_excess_return_pct": observed_mean,
            "random_mean_net_excess_return_pct": null_mean,
            "observed_minus_random_mean_pct_points": (
                observed_mean - null_mean
            ),
            "random_null_q05_pct": float(
                np.quantile(null_means, 0.05)
            ),
            "random_null_median_pct": float(
                np.quantile(null_means, 0.50)
            ),
            "random_null_q95_pct": float(
                np.quantile(null_means, 0.95)
            ),
            "nominal_one_sided_p_value": p_value,
            "permutations_completed": int(permutations),
        }

    return result
