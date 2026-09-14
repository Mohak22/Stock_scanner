# -*- coding: utf-8 -*-
"""
Created on Fri Sep  4 11:58:23 2026

@author: mohak
"""
# -*- coding: utf-8 -*-

"""
Research Condition Engine

Purpose:
    Apply research conditions against calculated dataframe features.

Supports:
    - Numeric comparisons
    - Feature-to-feature comparisons
    - Parameterized features such as:
        RSI(9)
        RSI(14)
        EMA(20)
        SMA(50)
        Return(5)
        Average Volume(20)
        Average Delivery %(20)

The feature period is resolved dynamically to the actual
calculated dataframe column.
"""

import pandas as pd


# ======================================================================
# FEATURE COLUMN RESOLUTION
# ======================================================================

def _resolve_feature_column(
    dataframe: pd.DataFrame,
    feature: str,
    period=None,
) -> str:
    """
    Resolve a logical feature name to the actual dataframe column.

    Examples:

        rsi + 14
            -> RSI_14

        rsi + 9
            -> RSI_9

        ema + 20
            -> EMA_20

        return + 5
            -> RETURN_5

    Non-parameterized features such as CLOSE or VOLUME are also
    resolved case-insensitively.
    """

    feature = str(feature).strip()

    candidates = []

    # ----------------------------------------------------------
    # Parameterized feature
    # ----------------------------------------------------------

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

    # ----------------------------------------------------------
    # Non-parameterized feature
    # ----------------------------------------------------------

    candidates.extend(
        [
            feature,
            feature.upper(),
            feature.lower(),
        ]
    )

    # ----------------------------------------------------------
    # Direct match
    # ----------------------------------------------------------

    for candidate in candidates:

        if candidate in dataframe.columns:
            return candidate

    # ----------------------------------------------------------
    # Case-insensitive fallback
    # ----------------------------------------------------------

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


# ======================================================================
# CONDITION ENGINE
# ======================================================================

def apply_conditions(
    dataframe: pd.DataFrame,
    conditions: list[dict]
) -> pd.Series:

    if not conditions:

        return pd.Series(
            True,
            index=dataframe.index
        )

    signal = pd.Series(
        True,
        index=dataframe.index
    )

    for condition in conditions:

        # ----------------------------------------------------------
        # Read condition
        # ----------------------------------------------------------

        left_feature = condition["feature"]
        operator = condition["operator"]
        right_value = condition["value"]

        # ----------------------------------------------------------
        # Optional period for LEFT feature
        # ----------------------------------------------------------

        left_period = condition.get("period")

        left_column = _resolve_feature_column(
            dataframe=dataframe,
            feature=left_feature,
            period=left_period,
        )

        left_series = dataframe[left_column]

        # ----------------------------------------------------------
        # RIGHT SIDE
        #
        # Can be:
        #
        # 1. Numeric value
        # 2. Another feature
        # 3. Parameterized feature
        # ----------------------------------------------------------

        if isinstance(right_value, dict):

            right_feature = right_value["feature"]
            right_period = right_value.get("period")

            right_column = _resolve_feature_column(
                dataframe=dataframe,
                feature=right_feature,
                period=right_period,
            )

            right_series = dataframe[right_column]

        elif isinstance(right_value, str):

            # Existing format where a dataframe column name
            # is supplied directly.
            #
            # This also supports plain feature names.

            right_series = dataframe[
                _resolve_feature_column(
                    dataframe=dataframe,
                    feature=right_value,
                )
            ]

        else:

            right_series = right_value

        # ----------------------------------------------------------
        # COMPARISON
        # ----------------------------------------------------------

        if operator == "<":

            current_condition = (
                left_series < right_series
            )

        elif operator == "<=":

            current_condition = (
                left_series <= right_series
            )

        elif operator == ">":

            current_condition = (
                left_series > right_series
            )

        elif operator == ">=":

            current_condition = (
                left_series >= right_series
            )

        elif operator == "==":

            current_condition = (
                left_series == right_series
            )

        elif operator == "!=":

            current_condition = (
                left_series != right_series
            )

        else:

            raise ValueError(
                f"Unsupported operator: {operator}"
            )

        # ----------------------------------------------------------
        # MULTIPLE CONDITIONS = AND
        # ----------------------------------------------------------

        signal = signal & current_condition

    return signal