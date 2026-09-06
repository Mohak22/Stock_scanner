# -*- coding: utf-8 -*-
"""
Created on Fri Sep  4 11:52:40 2026

@author: mohak
"""

from __future__ import annotations

import pandas as pd

from indicators.ema_engine import calculate_ema
from indicators.rsi_engine import calculate_rsi_series


def calculate_sma_series(
    values: pd.Series,
    period: int
) -> pd.Series:
    if period <= 0:
        raise ValueError("period must be greater than zero.")

    return values.rolling(
        window=period,
        min_periods=period
    ).mean()


def calculate_average_volume(
    volume: pd.Series,
    period: int
) -> pd.Series:
    return calculate_sma_series(volume, period)


def calculate_average_delivery_percentage(
    delivery_percentage: pd.Series,
    period: int
) -> pd.Series:
    return calculate_sma_series(delivery_percentage, period)


def calculate_return_series(
    close_prices: pd.Series,
    period: int
) -> pd.Series:
    if period <= 0:
        raise ValueError("period must be greater than zero.")

    return (
        close_prices
        .pct_change(periods=period)
        * 100
    )


def calculate_features(
    dataframe: pd.DataFrame,
    features: list[dict]
) -> pd.DataFrame:

    required_columns = {
        "SYMBOL",
        "TIMESTAMP",
        "CLOSE",
    }

    missing_columns = required_columns - set(dataframe.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    result = dataframe.copy()

    result["TIMESTAMP"] = pd.to_datetime(result["TIMESTAMP"])

    result = result.sort_values(
        ["SYMBOL", "TIMESTAMP"]
    ).reset_index(drop=True)

    for feature in features:

        feature_type = feature["type"].lower()
        period = feature.get("period")

        if period is not None:
            period = int(period)

        if feature_type == "rsi":

            if period is None:
                raise ValueError(
                    "RSI requires a period."
                )

            result[f"RSI_{period}"] = (
                result
                .groupby("SYMBOL")["CLOSE"]
                .transform(
                    lambda x: calculate_rsi_series(
                        x,
                        period
                    )
                )
            )

        elif feature_type == "ema":

            if period is None:
                raise ValueError(
                    "EMA requires a period."
                )

            result[f"EMA_{period}"] = (
                result
                .groupby("SYMBOL")["CLOSE"]
                .transform(
                    lambda x: calculate_ema(
                        x,
                        period
                    )
                )
            )

        elif feature_type == "sma":

            if period is None:
                raise ValueError(
                    "SMA requires a period."
                )

            result[f"SMA_{period}"] = (
                result
                .groupby("SYMBOL")["CLOSE"]
                .transform(
                    lambda x: calculate_sma_series(
                        x,
                        period
                    )
                )
            )

        elif feature_type == "volume":

            result["VOLUME"] = result["TOTTRDQTY"]

        elif feature_type == "average_volume":

            if period is None:
                raise ValueError(
                    "Average Volume requires a period."
                )

            result[f"AVG_VOLUME_{period}"] = (
                result
                .groupby("SYMBOL")["TOTTRDQTY"]
                .transform(
                    lambda x: calculate_average_volume(
                        x,
                        period
                    )
                )
            )

        elif feature_type == "delivery_percentage":

            if "DELIV_PER" not in result.columns:
                raise ValueError(
                    "DELIV_PER column is required "
                    "for delivery_percentage."
                )

            result["DELIVERY_PERCENTAGE"] = (
                result["DELIV_PER"]
            )

        elif feature_type == "average_delivery_percentage":

            if period is None:
                raise ValueError(
                    "Average Delivery % requires a period."
                )

            if "DELIV_PER" not in result.columns:
                raise ValueError(
                    "DELIV_PER column is required "
                    "for average_delivery_percentage."
                )

            result[f"AVG_DELIVERY_PERCENTAGE_{period}"] = (
                result
                .groupby("SYMBOL")["DELIV_PER"]
                .transform(
                    lambda x: calculate_average_delivery_percentage(
                        x,
                        period
                    )
                )
            )

        elif feature_type == "return":

            if period is None:
                raise ValueError(
                    "Return requires a period."
                )

            result[f"RETURN_{period}"] = (
                result
                .groupby("SYMBOL")["CLOSE"]
                .transform(
                    lambda x: calculate_return_series(
                        x,
                        period
                    )
                )
            )

        else:
            raise ValueError(
                f"Unsupported feature type: {feature_type}"
            )

    return result