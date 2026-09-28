# -*- coding: utf-8 -*-
"""
Research Condition Engine

Purpose:
    Apply research conditions against calculated dataframe features.

Supports:
    - Numeric comparisons
    - Feature-to-feature comparisons
    - Parameterized features
    - Arithmetic multiplier expressions
"""

from __future__ import annotations

import pandas as pd


def _resolve_feature_column(
    dataframe: pd.DataFrame,
    feature: str,
    period=None,
) -> str:
    feature = str(feature).strip()

    candidates = []

    if period is not None:
        try:
            period = int(period)
        except (TypeError, ValueError):
            raise ValueError(
                f"Invalid period '{period}' for feature '{feature}'."
            )

        if period <= 0:
            raise ValueError(
                f"Period must be greater than zero. "
                f"Received {period} for feature '{feature}'."
            )

        candidates.extend(
            [
                f"{feature}_{period}",
                f"{feature.upper()}_{period}",
                f"{feature.lower()}_{period}",
            ]
        )

    candidates.extend(
        [
            feature,
            feature.upper(),
            feature.lower(),
        ]
    )

    for candidate in candidates:
        if candidate in dataframe.columns:
            return candidate

    lookup = {
        str(column).upper(): column
        for column in dataframe.columns
    }

    for candidate in candidates:
        key = str(candidate).upper()
        if key in lookup:
            return lookup[key]

    raise ValueError(
        f"Feature '{feature}'"
        + (
            f" with period {period}"
            if period is not None
            else ""
        )
        + " not found in dataframe."
    )


def _resolve_right_expression(
    dataframe: pd.DataFrame,
    right_value,
):
    """
    Resolve the right-hand side of a condition.

    Supported forms:
        30
        {"feature": "ema", "period": 50}
        {"feature": "average_volume", "period": 20, "multiplier": 2}
        {"value": 30, "multiplier": 2}
    """

    if isinstance(right_value, dict):
        if "feature" in right_value:
            right_column = _resolve_feature_column(
                dataframe=dataframe,
                feature=right_value["feature"],
                period=right_value.get("period"),
            )
            base_value = dataframe[right_column]

        elif "value" in right_value:
            base_value = right_value["value"]

        else:
            raise ValueError(
                "Right-hand expression must contain either "
                "'feature' or 'value'."
            )

        multiplier = right_value.get(
            "multiplier",
            1,
        )

        try:
            multiplier = float(multiplier)
        except (TypeError, ValueError):
            raise ValueError(
                f"Invalid arithmetic multiplier: {multiplier}"
            )

        if multiplier < 0:
            raise ValueError(
                "Arithmetic multiplier must be non-negative."
            )

        return base_value * multiplier

    if isinstance(right_value, str):
        return dataframe[
            _resolve_feature_column(
                dataframe=dataframe,
                feature=right_value,
            )
        ]

    return right_value


def apply_conditions(
    dataframe: pd.DataFrame,
    conditions: list[dict],
) -> pd.Series:

    if not conditions:
        return pd.Series(
            True,
            index=dataframe.index,
        )

    signal = pd.Series(
        True,
        index=dataframe.index,
    )

    for condition in conditions:
        left_feature = condition["feature"]
        operator = condition["operator"]
        right_value = condition["value"]

        left_column = _resolve_feature_column(
            dataframe=dataframe,
            feature=left_feature,
            period=condition.get("period"),
        )

        left_series = dataframe[left_column]

        right_series = _resolve_right_expression(
            dataframe=dataframe,
            right_value=right_value,
        )

        if operator == "<":
            current_condition = left_series < right_series
        elif operator == "<=":
            current_condition = left_series <= right_series
        elif operator == ">":
            current_condition = left_series > right_series
        elif operator == ">=":
            current_condition = left_series >= right_series
        elif operator == "==":
            current_condition = left_series == right_series
        elif operator == "!=":
            current_condition = left_series != right_series
        else:
            raise ValueError(
                f"Unsupported operator: {operator}"
            )

        signal = signal & current_condition.fillna(False)

    return signal
