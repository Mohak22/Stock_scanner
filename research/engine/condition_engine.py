# -*- coding: utf-8 -*-
"""
Created on Fri Sep  4 11:58:23 2026

@author: mohak
"""

import pandas as pd


def apply_conditions(
    dataframe: pd.DataFrame,
    conditions: list[dict]
) -> pd.Series:

    if not conditions:
        return pd.Series(True, index=dataframe.index)

    signal = pd.Series(
        True,
        index=dataframe.index
    )

    for condition in conditions:

        left_feature = condition["feature"]
        operator = condition["operator"]
        right_value = condition["value"]

        if left_feature not in dataframe.columns:
            raise ValueError(
                f"Feature '{left_feature}' not found in dataframe."
            )

        left_series = dataframe[left_feature]

        # ----------------------------------------------------------
        # Right side can be either:
        # 1. Numeric value
        # 2. Another dataframe column
        # ----------------------------------------------------------

        if isinstance(right_value, str):

            if right_value not in dataframe.columns:
                raise ValueError(
                    f"Feature '{right_value}' not found in dataframe."
                )

            right_series = dataframe[right_value]

        else:
            right_series = right_value

        # ----------------------------------------------------------
        # Comparison
        # ----------------------------------------------------------

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

        # ----------------------------------------------------------
        # Multiple conditions = AND
        # ----------------------------------------------------------

        signal = signal & current_condition

    return signal