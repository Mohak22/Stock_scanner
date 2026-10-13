# -*- coding: utf-8 -*-
"""
Created on Fri Sep  4 12:03:36 2026

@author: mohak
"""

"""
Research engine for the Stock Scanner Research Cockpit.

Responsibilities:

1. Apply strategy entry conditions.
2. Calculate stock forward returns.
3. Calculate aggregate stock performance.
4. Calculate market-relative performance.
5. Analyze performance by stock.
6. Analyze performance by feature value.
7. Analyze performance by market regime.
8. Build research diagnostics.

Important architecture:

- This engine calculates signals and stock forward returns on the
  COMPLETE extended dataset.
- Training / Validation / Testing splitting is handled by api/main.py.
- Market forward returns and market regime are attached by api/main.py.
- The engine never uses future information to create a signal.
"""

import numpy as np
import pandas as pd

from research.engine.condition_engine import apply_conditions
from research.engine.return_engine import calculate_forward_returns
from research.engine.feature_engine import calculate_features

# ======================================================================
# HELPERS
# ======================================================================

def _safe_float(value):
    """
    Convert a value to a JSON-safe float.
    """

    if value is None:
        return None

    try:
        value = float(value)
    except (TypeError, ValueError):
        return None

    if not np.isfinite(value):
        return None

    return value


def _round(value, digits=4):
    """
    Safely round a numeric value.
    """

    value = _safe_float(value)

    if value is None:
        return None

    return round(value, digits)


# ======================================================================
# PERFORMANCE METRICS
# ======================================================================

def _performance_metrics(
    dataframe: pd.DataFrame,
    return_column: str,
    market_column: str | None = None,
    excess_column: str | None = None,
) -> dict:
    """
    Calculate stock, market and excess-return metrics.
    """

    result = {
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

    if return_column not in dataframe.columns:
        return result

    stock_returns = pd.to_numeric(
        dataframe[return_column],
        errors="coerce",
    ).dropna()

    result["observations"] = int(
        len(stock_returns)
    )

    if stock_returns.empty:
        return result

    result["average_return"] = _round(
        stock_returns.mean()
    )

    result["median_return"] = _round(
        stock_returns.median()
    )

    result["positive_return_pct"] = _round(
        (stock_returns > 0).mean() * 100,
        2,
    )

    result["negative_return_pct"] = _round(
        (stock_returns < 0).mean() * 100,
        2,
    )

    result["best_return"] = _round(
        stock_returns.max()
    )

    result["worst_return"] = _round(
        stock_returns.min()
    )

    # ----------------------------------------------------------
    # Market
    # ----------------------------------------------------------

    if market_column is not None:

        if market_column in dataframe.columns:

            market_returns = pd.to_numeric(
                dataframe[market_column],
                errors="coerce",
            ).dropna()

            result["market_observations"] = int(
                len(market_returns)
            )

            if not market_returns.empty:

                result["average_market_return"] = _round(
                    market_returns.mean()
                )

                result["median_market_return"] = _round(
                    market_returns.median()
                )

    # ----------------------------------------------------------
    # Excess
    # ----------------------------------------------------------

    if excess_column is not None:

        if excess_column in dataframe.columns:

            excess_returns = pd.to_numeric(
                dataframe[excess_column],
                errors="coerce",
            ).dropna()

            result["excess_observations"] = int(
                len(excess_returns)
            )

            if not excess_returns.empty:

                result["average_excess_return"] = _round(
                    excess_returns.mean()
                )

                result["median_excess_return"] = _round(
                    excess_returns.median()
                )

                result["outperformed_market_pct"] = _round(
                    (excess_returns > 0).mean() * 100,
                    2,
                )

    return result


# ======================================================================
# A3.1 — ANALYSIS BY STOCK
# ======================================================================

def analyze_by_stock(
    signal_data: pd.DataFrame,
    horizons: list[int],
) -> dict:
    """
    Analyze performance separately for every stock.
    """

    if signal_data.empty:
        return {}

    if "SYMBOL" not in signal_data.columns:
        return {}

    result = {}

    for symbol, stock_data in signal_data.groupby(
        "SYMBOL",
        sort=True,
    ):

        stock_result = {
            "signal_count": int(
                len(stock_data)
            ),
            "performance": {},
        }

        for horizon in horizons:

            horizon = int(horizon)

            stock_result["performance"][
                f"T+{horizon}"
            ] = _performance_metrics(
                dataframe=stock_data,
                return_column=f"RETURN_T{horizon}",
                market_column=f"MARKET_RETURN_T{horizon}",
                excess_column=f"EXCESS_RETURN_T{horizon}",
            )

        result[str(symbol)] = stock_result

    return result


# ======================================================================
# A3.2 — FEATURE BUCKETING
# ======================================================================

def _resolve_feature_column(
    signal_data: pd.DataFrame,
    feature: dict,
):
    """
    Resolve the actual dataframe column corresponding to a feature
    configuration.
    """

    feature_type = str(
        feature.get("type", "")
    ).strip()

    period = feature.get("period")

    candidates = []

    if period is not None:

        try:
            period = int(period)
        except (
            TypeError,
            ValueError,
        ):
            period = None

    if period is not None:

        candidates.extend(
            [
                f"{feature_type}_{period}",
                f"{feature_type.upper()}_{period}",
                f"{feature_type.lower()}_{period}",
            ]
        )

    candidates.extend(
        [
            feature_type,
            feature_type.upper(),
            feature_type.lower(),
        ]
    )

    for candidate in candidates:

        if candidate in signal_data.columns:
            return candidate

    # Case-insensitive fallback.
    lookup = {
        str(column).upper(): column
        for column in signal_data.columns
    }

    for candidate in candidates:

        key = str(candidate).upper()

        if key in lookup:
            return lookup[key]

    return None


def _make_feature_buckets(
    series: pd.Series,
) -> pd.Series:
    """
    Create quartile buckets from signal-time feature values.

    Q1_LOW
    Q2
    Q3
    Q4_HIGH

    If quartile bucketing is impossible, ALL is used.
    """

    values = pd.to_numeric(
        series,
        errors="coerce",
    )

    buckets = pd.Series(
        pd.NA,
        index=series.index,
        dtype="object",
    )

    valid = values.notna()

    if not valid.any():
        return buckets

    valid_values = values.loc[valid]

    if valid_values.nunique() < 2:

        buckets.loc[valid] = "ALL"

        return buckets

    try:

        qcut_result = pd.qcut(
            valid_values,
            q=4,
            labels=[
                "Q1_LOW",
                "Q2",
                "Q3",
                "Q4_HIGH",
            ],
            duplicates="drop",
        )

        buckets.loc[valid] = (
            qcut_result.astype(str)
        )

    except ValueError:

        buckets.loc[valid] = "ALL"

    return buckets


# ======================================================================
# A3.2 — ANALYSIS BY FEATURE
# ======================================================================

def analyze_by_feature(
    signal_data: pd.DataFrame,
    features: list[dict],
    horizons: list[int],
) -> dict:
    """
    Analyze signal performance by feature-value bucket.

    The feature value is the value present at signal time.
    """

    if signal_data.empty:
        return {}

    result = {}

    for feature in features:

        feature_column = _resolve_feature_column(
            signal_data=signal_data,
            feature=feature,
        )

        if feature_column is None:
            continue

        feature_data = signal_data.copy()

        feature_data["_FEATURE_BUCKET"] = (
            _make_feature_buckets(
                feature_data[
                    feature_column
                ]
            )
        )

        feature_data = feature_data[
            feature_data["_FEATURE_BUCKET"].notna()
        ].copy()

        if feature_data.empty:
            continue

        feature_result = {
            "column": feature_column,
            "buckets": {},
        }

        for bucket, bucket_data in feature_data.groupby(
            "_FEATURE_BUCKET",
            sort=True,
        ):

            numeric_values = pd.to_numeric(
                bucket_data[
                    feature_column
                ],
                errors="coerce",
            )

            bucket_result = {
                "signal_count": int(
                    len(bucket_data)
                ),
                "feature_min": _round(
                    numeric_values.min()
                ),
                "feature_max": _round(
                    numeric_values.max()
                ),
                "performance": {},
            }

            for horizon in horizons:

                horizon = int(horizon)

                bucket_result["performance"][
                    f"T+{horizon}"
                ] = _performance_metrics(
                    dataframe=bucket_data,
                    return_column=f"RETURN_T{horizon}",
                    market_column=f"MARKET_RETURN_T{horizon}",
                    excess_column=f"EXCESS_RETURN_T{horizon}",
                )

            feature_result["buckets"][
                str(bucket)
            ] = bucket_result

        result[feature_column] = feature_result

    return result


# ======================================================================
# A3.3 — ANALYSIS BY MARKET REGIME
# ======================================================================

def analyze_by_market_regime(
    signal_data: pd.DataFrame,
    horizons: list[int],
) -> dict:
    """
    Analyze strategy performance separately under:

        BULL
        NEUTRAL
        BEAR

    MARKET_REGIME must already have been attached by the
    causal regime engine.
    """

    if signal_data.empty:
        return {}

    if "MARKET_REGIME" not in signal_data.columns:
        return {}

    result = {}

    for regime in [
        "BULL",
        "NEUTRAL",
        "BEAR",
    ]:

        regime_data = signal_data[
            signal_data["MARKET_REGIME"]
            == regime
        ].copy()

        regime_result = {
            "signal_count": int(
                len(regime_data)
            ),
            "performance": {},
        }

        for horizon in horizons:

            horizon = int(horizon)

            regime_result["performance"][
                f"T+{horizon}"
            ] = _performance_metrics(
                dataframe=regime_data,
                return_column=f"RETURN_T{horizon}",
                market_column=f"MARKET_RETURN_T{horizon}",
                excess_column=f"EXCESS_RETURN_T{horizon}",
            )

        result[regime] = regime_result

    return result


# ======================================================================
# COMPLETE A3 ANALYSIS
# ======================================================================

def build_research_analysis(
    signal_data: pd.DataFrame,
    features: list[dict],
    horizons: list[int],
) -> dict:
    """
    Build all A3 analysis dimensions.
    """

    return {
        "by_stock": analyze_by_stock(
            signal_data=signal_data,
            horizons=horizons,
        ),
        "by_feature": analyze_by_feature(
            signal_data=signal_data,
            features=features,
            horizons=horizons,
        ),
        "by_market_regime": analyze_by_market_regime(
            signal_data=signal_data,
            horizons=horizons,
        ),
    }


# ======================================================================
# DIAGNOSTICS
# ======================================================================

def build_research_diagnostics(
    dataframe: pd.DataFrame,
    signal_data: pd.DataFrame,
    horizons: list[int],
    features: list[dict] | None = None,
) -> dict:
    """
    Build diagnostics and A3 analysis for one research split.
    """

    if dataframe is None:
        raise ValueError(
            "Historical dataframe cannot be None."
        )

    if signal_data is None:
        raise ValueError(
            "Signal dataframe cannot be None."
        )

    total_rows = int(
        len(dataframe)
    )

    signal_count = int(
        len(signal_data)
    )

    signal_rate = (
        signal_count / total_rows * 100
        if total_rows > 0
        else 0.0
    )

    # ----------------------------------------------------------
    # Stock coverage
    # ----------------------------------------------------------

    if (
        not signal_data.empty
        and "SYMBOL" in signal_data.columns
    ):

        stocks_with_signals = int(
            signal_data["SYMBOL"].nunique()
        )

    else:

        stocks_with_signals = 0

    # ----------------------------------------------------------
    # Signal date range
    # ----------------------------------------------------------

    signal_date_range = {
        "start": None,
        "end": None,
    }

    if (
        not signal_data.empty
        and "TIMESTAMP" in signal_data.columns
    ):

        timestamps = pd.to_datetime(
            signal_data["TIMESTAMP"],
            errors="coerce",
        ).dropna()

        if not timestamps.empty:

            signal_date_range = {
                "start": (
                    timestamps.min()
                    .strftime("%Y-%m-%d")
                ),
                "end": (
                    timestamps.max()
                    .strftime("%Y-%m-%d")
                ),
            }

    # ----------------------------------------------------------
    # Sample quality
    # ----------------------------------------------------------

    if signal_count == 0:

        sample_classification = "NONE"

    elif signal_count < 10:

        sample_classification = "VERY_LOW"

    elif signal_count < 30:

        sample_classification = "LOW"

    else:

        sample_classification = "ADEQUATE"

    # ----------------------------------------------------------
    # Stock coverage quality
    # ----------------------------------------------------------

    if stocks_with_signals == 0:

        stock_classification = "NONE"

    elif stocks_with_signals < 3:

        stock_classification = "LOW"

    else:

        stock_classification = "ADEQUATE"

    # ----------------------------------------------------------
    # Performance + outcomes
    # ----------------------------------------------------------

    performance = {}
    outcome_quality = {}
    warnings = []

    for horizon in horizons:

        horizon = int(horizon)

        return_column = (
            f"RETURN_T{horizon}"
        )

        if return_column not in signal_data.columns:

            raise ValueError(
                f"Expected return column "
                f"'{return_column}' was not found."
            )

        stock_returns = pd.to_numeric(
            signal_data[
                return_column
            ],
            errors="coerce",
        ).dropna()

        observations = int(
            len(stock_returns)
        )

        performance[
            f"T+{horizon}"
        ] = _performance_metrics(
            dataframe=signal_data,
            return_column=return_column,
            market_column=(
                f"MARKET_RETURN_T{horizon}"
            ),
            excess_column=(
                f"EXCESS_RETURN_T{horizon}"
            ),
        )

        if observations == 0:

            classification = "NONE"

            warnings.append(
                f"NO_VALID_OUTCOMES_T{horizon}"
            )

        elif observations < 10:

            classification = "LOW"

            warnings.append(
                f"LOW_VALID_OUTCOMES_T{horizon}"
            )

        else:

            classification = "ADEQUATE"

        outcome_quality[
            f"T+{horizon}"
        ] = {
            "valid_observations": observations,
            "classification": classification,
        }

    # ----------------------------------------------------------
    # General warnings
    # ----------------------------------------------------------

    if signal_count == 0:

        warnings.append(
            "NO_SIGNALS"
        )

    elif signal_count < 10:

        warnings.append(
            "VERY_LOW_SIGNAL_COUNT"
        )

    elif signal_count < 30:

        warnings.append(
            "LOW_SIGNAL_COUNT"
        )

    if stocks_with_signals == 0:

        warnings.append(
            "NO_STOCK_COVERAGE"
        )

    elif stocks_with_signals < 3:

        warnings.append(
            "LOW_STOCK_COVERAGE"
        )


    # ----------------------------------------------------------
    # Survivorship sensitivity: exclude top 10% of symbols
    # ----------------------------------------------------------
    # This is a descriptive concentration stress test, NOT a
    # correction for survivorship bias.
    #
    # For each horizon:
    # 1. Calculate each symbol's mean realized forward return.
    # 2. Rank symbols by that mean return.
    # 3. Exclude the top ceil(10%) of symbols.
    # 4. Recalculate aggregate returns on the remaining signals.
    #
    # Important limitation:
    # The ranking uses realized outcomes from the same sample.
    # Therefore, this is not an unbiased performance estimate,
    # and the excluded symbols must not be treated as a trading rule.

    survivorship_sensitivity = {
        "method": (
            "For each horizon, rank symbols with valid signal "
            "outcomes by mean realized forward return; exclude "
            "the top ceil(10%) of symbols and recompute metrics."
        ),
        "interpretation": (
            "Descriptive concentration stress test only. "
            "The ranking uses realized evaluation outcomes, "
            "so this is not an unbiased performance estimate "
            "and must not be used as a tradable rule."
        ),
        "top_fraction": 0.10,
        "by_horizon": {},
    }

    if (
        not signal_data.empty
        and "SYMBOL" in signal_data.columns
    ):
        for horizon in horizons:
            horizon = int(horizon)
            return_column = f"RETURN_T{horizon}"

            if return_column not in signal_data.columns:
                continue

            valid = signal_data[
                ["SYMBOL", return_column]
            ].copy()

            valid[return_column] = pd.to_numeric(
                valid[return_column],
                errors="coerce",
            )

            valid = valid.dropna(
                subset=["SYMBOL", return_column]
            )

            # Deterministic ranking for reproducibility.
            symbol_means = (
                valid.groupby("SYMBOL")[return_column]
                .mean()
                .sort_values(
                    ascending=False,
                    kind="mergesort",
                )
            )

            symbol_count = int(len(symbol_means))

            excluded_count = (
                int(np.ceil(symbol_count * 0.10))
                if symbol_count >= 2
                else 0
            )

            excluded_symbols = (
                symbol_means.index[:excluded_count].tolist()
                if excluded_count > 0
                else []
            )

            remaining = signal_data[
                ~signal_data["SYMBOL"].isin(excluded_symbols)
            ].copy()

            full_metrics = _performance_metrics(
                dataframe=signal_data,
                return_column=return_column,
            )

            remaining_metrics = _performance_metrics(
                dataframe=remaining,
                return_column=return_column,
            )

            survivorship_sensitivity["by_horizon"][
                f"T+{horizon}"
            ] = {
                "symbols_with_valid_outcomes": symbol_count,
                "excluded_top_symbols_count": excluded_count,
                "excluded_top_symbols": excluded_symbols,
                "remaining_symbols_with_signals": (
                    int(remaining["SYMBOL"].nunique())
                    if not remaining.empty
                    else 0
                ),
                "all_symbols_average_return": (
                    full_metrics["average_return"]
                ),
                "remaining_average_return": (
                    remaining_metrics["average_return"]
                ),
                "remaining_median_return": (
                    remaining_metrics["median_return"]
                ),
                "remaining_observations": (
                    remaining_metrics["observations"]
                ),
            }

    # ----------------------------------------------------------
    # A3 analysis
    # ----------------------------------------------------------

    if features is None:
        features = []

    analysis = build_research_analysis(
        signal_data=signal_data,
        features=features,
        horizons=horizons,
    )

    # ----------------------------------------------------------
    # Return
    # ----------------------------------------------------------

    return {
        "summary": {
            "total_rows": total_rows,
            "signal_count": signal_count,
            "signal_rate": _round(
                signal_rate,
                2,
            ),
            "stocks_with_signals": (
                stocks_with_signals
            ),
            "signal_date_range": (
                signal_date_range
            ),
        },

        "performance": performance,

        "diagnostics": {
            "sample_quality": {
                "signal_count": signal_count,
                "classification": (
                    sample_classification
                ),
            },

            "stock_coverage": {
                "stocks_with_signals": (
                    stocks_with_signals
                ),
                "classification": (
                    stock_classification
                ),
            },

            "outcome_quality": outcome_quality,
        },

        "survivorship_sensitivity": survivorship_sensitivity,

        "analysis": analysis,

        "warnings": sorted(
            set(warnings)
        ),
    }


# ======================================================================
# MAIN RESEARCH EXECUTION
# ======================================================================

def run_research(
    dataframe: pd.DataFrame,
    features: list[dict],
    conditions: list[dict],
    horizons: list[int],
) -> dict:
    """
    Execute research on the COMPLETE extended dataset.

    This function intentionally does NOT split the data into
    Training / Validation / Testing.

    api/main.py performs the split AFTER this function has
    calculated signals and forward returns across the full
    dataset.
    """

    if dataframe is None:

        raise ValueError(
            "Historical dataframe cannot be None."
        )

    if dataframe.empty:

        raise ValueError(
            "Historical dataframe is empty."
        )

    required_columns = {
        "SYMBOL",
        "TIMESTAMP",
    }

    missing_columns = (
        required_columns
        - set(dataframe.columns)
    )

    if missing_columns:

        raise ValueError(
            "Historical dataframe is missing "
            f"required columns: "
            f"{sorted(missing_columns)}"
        )

    # ----------------------------------------------------------
    # Normalize
    # ----------------------------------------------------------

    data = dataframe.copy()

    data["TIMESTAMP"] = pd.to_datetime(
        data["TIMESTAMP"],
        errors="coerce",
    )

    data = data.dropna(
        subset=[
            "SYMBOL",
            "TIMESTAMP",
        ]
    ).copy()

    data["SYMBOL"] = (
        data["SYMBOL"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    data = (
        data
        .sort_values(
            [
                "SYMBOL",
                "TIMESTAMP",
            ]
        )
        .reset_index(drop=True)
    )

    # ----------------------------------------------------------
    # Calculate requested research features
    # ----------------------------------------------------------

    data = calculate_features(
        dataframe=data,
        features=features,
    )

    # ----------------------------------------------------------
    # Apply conditions
    # ----------------------------------------------------------

    signal_mask = apply_conditions(
        dataframe=data,
        conditions=conditions,
    )

    if not isinstance(
        signal_mask,
        pd.Series,
    ):

        signal_mask = pd.Series(
            signal_mask,
            index=data.index,
        )

    signal_mask = (
        signal_mask
        .fillna(False)
        .astype(bool)
    )

    # ----------------------------------------------------------
    # Forward returns MUST be calculated on the complete
    # dataset before selecting signals.
    # ----------------------------------------------------------

    data_with_returns = (
        calculate_forward_returns(
            dataframe=data,
            horizons=horizons,
        )
    )

    # ----------------------------------------------------------
    # Select signal rows
    # ----------------------------------------------------------

    signal_data = (
        data_with_returns.loc[
            signal_mask
        ].copy()
    )

    signal_data = (
        signal_data
        .sort_values(
            [
                "SYMBOL",
                "TIMESTAMP",
            ]
        )
        .reset_index(drop=True)
    )

    # ----------------------------------------------------------
    # Base performance
    #
    # Market-relative fields are attached later by main.py.
    # ----------------------------------------------------------

    performance = {}

    for horizon in horizons:

        horizon = int(horizon)

        performance[
            f"T+{horizon}"
        ] = _performance_metrics(
            dataframe=signal_data,
            return_column=f"RETURN_T{horizon}",
        )

    # ----------------------------------------------------------
    # Diagnostics
    #
    # At this stage market-relative analysis is empty because
    # main.py attaches market data after this function returns.
    # ----------------------------------------------------------

    diagnostics = build_research_diagnostics(
        dataframe=data_with_returns,
        signal_data=signal_data,
        horizons=horizons,
        features=features,
    )

    return {
        "summary": diagnostics["summary"],
        "performance": performance,
        "diagnostics": diagnostics["diagnostics"],
        "analysis": diagnostics["analysis"],
        "warnings": diagnostics["warnings"],
        "signals": signal_data,
    }