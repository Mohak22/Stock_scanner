"""
Explicit, causal temporal evaluation for rule-based research.

Temporal convention
-------------------

Signal:
    Generated using information available for the signal date.

Entry:
    Same-day CLOSE price proxy.

T+1 / BTST:
    Next available trading session's CLOSE.

T+N for N > 1:
    Close of the N-th subsequent available trading session.

Trading sessions are based on the observations available for each
symbol. Weekends and exchange holidays do not count as horizons.

Stage boundaries are strict:
    Both the signal date and outcome date must lie within the stage.

This module evaluates historical research outcomes. It does not
guarantee real-world order execution or returns.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from research.engine.condition_engine import apply_conditions


TEMPORAL_CONVENTION = {
    "signal_observation": "signal_date",
    "entry": "same signal_date close proxy",
    "entry_price_basis": "CLOSE",
    "t1_outcome": "next available symbol session CLOSE",
    "t1_outcome_price_basis": "NEXT_SESSION_CLOSE",
    "t1_outcome_type": "close_to_close_return",
    "outcome": (
        "N-th subsequent available symbol session CLOSE"
    ),
    "outcome_price_basis": "CLOSE",
    "horizon_anchor": "signal_date",
    "stage_boundary_policy": (
        "strict_signal_and_outcome_within_stage"
    ),
}


@dataclass(frozen=True)
class TemporalStage:
    """Inclusive signal and outcome window for one stage."""

    name: str
    start: pd.Timestamp
    end: pd.Timestamp

    @classmethod
    def create(
        cls,
        name: str,
        start: pd.Timestamp | str,
        end: pd.Timestamp | str,
    ) -> "TemporalStage":

        start_value = pd.Timestamp(start).normalize()
        end_value = pd.Timestamp(end).normalize()

        if start_value > end_value:
            raise ValueError(
                "Stage start must be on or before stage end."
            )

        return cls(
            name=name,
            start=start_value,
            end=end_value,
        )


def feature_lookback_requirements(
    features: Iterable[dict],
) -> dict[str, int]:
    """Return observation requirements for supported features."""

    requirements: dict[str, int] = {}

    for feature in features:

        feature_type = str(
            feature.get("type", "")
        ).lower()

        parameters = dict(
            feature.get("parameters") or {}
        )

        period = parameters.get(
            "period",
            feature.get("period"),
        )

        if period is not None:

            try:
                period = int(period)

            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid feature period: {feature}"
                ) from exc

            if period <= 0:
                raise ValueError(
                    f"Feature period must be positive: {feature}"
                )

        if feature_type in {
            "open",
            "high",
            "low",
            "close",
            "volume",
            "delivery_percentage",
            "delivery_quantity",
        }:
            required = 1

        elif feature_type == "ema":

            if period is None:
                raise ValueError("ema requires a period.")

            required = period + 1

        elif feature_type in {
            "sma",
            "average_volume",
            "average_delivery_percentage",
            "volume_average",
            "delivery_percentage_average",
        }:

            if period is None:
                raise ValueError(
                    f"{feature_type} requires a period."
                )

            required = period

        elif feature_type in {"return", "rsi"}:

            if period is None:
                raise ValueError(
                    f"{feature_type} requires a period."
                )

            required = period + 1

        else:
            continue

        key = (
            f"{feature_type}:{period}"
            if period is not None
            else feature_type
        )

        requirements[key] = required

    return requirements


def generate_signal_mask(
    dataframe: pd.DataFrame,
    conditions: list[dict],
) -> pd.Series:
    """Generate a Boolean signal mask from a feature-enriched dataframe."""

    signal_mask = apply_conditions(
        dataframe,
        conditions,
    )

    return (
        signal_mask
        .fillna(False)
        .astype(bool)
    )


def _normalise_stock_data(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Validate and standardise stock observations."""

    required = {
        "SYMBOL",
        "TIMESTAMP",
        "CLOSE",
    }

    missing = required - set(dataframe.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    data = dataframe.copy()

    data["_TEMPORAL_ROW_ID"] = range(len(data))

    data["TIMESTAMP"] = (
        pd.to_datetime(
            data["TIMESTAMP"],
            errors="coerce",
        )
        .dt.normalize()
    )

    data["CLOSE"] = pd.to_numeric(
        data["CLOSE"],
        errors="coerce",
    )

    data["SYMBOL"] = (
        data["SYMBOL"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    data = data.dropna(
        subset=[
            "SYMBOL",
            "TIMESTAMP",
            "CLOSE",
        ]
    )

    # Invalid prices must not produce misleading returns.
    data = data[data["CLOSE"] > 0].copy()

    data = (
        data
        .sort_values(
            [
                "SYMBOL",
                "TIMESTAMP",
                "_TEMPORAL_ROW_ID",
            ]
        )
        .drop_duplicates(
            subset=[
                "SYMBOL",
                "TIMESTAMP",
            ],
            keep="last",
        )
        .reset_index(drop=True)
    )

    return data


def _normalise_market_data(
    market_dataframe: pd.DataFrame | None,
) -> pd.DataFrame | None:
    """Validate and standardise benchmark observations."""

    if market_dataframe is None:
        return None

    required = {
        "TIMESTAMP",
        "MARKET_CLOSE",
    }

    missing = required - set(market_dataframe.columns)

    if missing:
        raise ValueError(
            f"Market data missing columns: {sorted(missing)}"
        )

    market = market_dataframe.copy()

    market["TIMESTAMP"] = (
        pd.to_datetime(
            market["TIMESTAMP"],
            errors="coerce",
        )
        .dt.normalize()
    )

    market["MARKET_CLOSE"] = pd.to_numeric(
        market["MARKET_CLOSE"],
        errors="coerce",
    )

    market = market.dropna(
        subset=[
            "TIMESTAMP",
            "MARKET_CLOSE",
        ]
    )

    market = market[
        market["MARKET_CLOSE"] > 0
    ].copy()

    return (
        market
        .sort_values("TIMESTAMP")
        .drop_duplicates(
            subset=["TIMESTAMP"],
            keep="last",
        )
        .set_index("TIMESTAMP", drop=False)
    )


def _market_outcome(
    market: pd.DataFrame | None,
    signal_date: pd.Timestamp | None,
    outcome_date: pd.Timestamp | None,
    stage: TemporalStage,
) -> dict:
    """Calculate benchmark return over the stock's exact outcome window."""

    if market is None:
        return {
            "entry_date": None,
            "outcome_date": None,
            "return": None,
            "status": "MARKET_DATA_UNAVAILABLE",
        }

    if signal_date is None:
        return {
            "entry_date": None,
            "outcome_date": None,
            "return": None,
            "status": "MARKET_ENTRY_UNAVAILABLE",
        }

    if signal_date not in market.index:
        return {
            "entry_date": None,
            "outcome_date": None,
            "return": None,
            "status": "MARKET_ENTRY_UNAVAILABLE",
        }

    entry_row = market.loc[signal_date]
    entry_date = entry_row["TIMESTAMP"]

    if outcome_date is None:
        return {
            "entry_date": entry_date,
            "outcome_date": None,
            "return": None,
            "status": "MARKET_OUTCOME_UNAVAILABLE",
        }

    if not (stage.start <= outcome_date <= stage.end):
        return {
            "entry_date": entry_date,
            "outcome_date": outcome_date,
            "return": None,
            "status": "MARKET_OUTCOME_OUTSIDE_STAGE",
        }

    if outcome_date not in market.index:
        return {
            "entry_date": entry_date,
            "outcome_date": outcome_date,
            "return": None,
            "status": "MARKET_OUTCOME_UNAVAILABLE",
        }

    outcome_row = market.loc[outcome_date]
    entry_price = float(entry_row["MARKET_CLOSE"])
    outcome_price = float(outcome_row["MARKET_CLOSE"])

    if entry_price <= 0 or outcome_price <= 0:
        return {
            "entry_date": entry_date,
            "outcome_date": outcome_date,
            "return": None,
            "status": "MARKET_PRICE_INVALID",
        }

    market_return = (outcome_price / entry_price - 1) * 100

    return {
        "entry_date": entry_date,
        "outcome_date": outcome_date,
        "return": market_return,
        "status": "COMPLETE",
    }


def evaluate_temporal_stage(
    dataframe: pd.DataFrame,
    signal_mask: pd.Series,
    stage: TemporalStage,
    horizons: list[int],
    market_dataframe: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Evaluate signals and forward returns within a temporal stage.

    Entry:
        Signal-date CLOSE proxy.

    T+1:
        Next available symbol session CLOSE.

    T+N for N > 1:
        N-th subsequent available symbol session CLOSE.

    Each horizon is independently eligible. Signals must be inside
    the stage, and their outcome dates must also be inside the stage.
    """

    if (
        not horizons
        or any(
            isinstance(horizon, bool)
            or not isinstance(horizon, int)
            or horizon <= 0
            for horizon in horizons
        )
    ):
        raise ValueError(
            "Horizons must contain positive integers."
        )

    if len(signal_mask) != len(dataframe):
        raise ValueError(
            "signal_mask must align with dataframe rows."
        )

    original = dataframe.copy()

    original["_TEMPORAL_ROW_ID"] = range(len(original))

    original["_SIGNAL"] = (
        signal_mask
        .fillna(False)
        .astype(bool)
        .to_numpy()
    )

    data = _normalise_stock_data(original)

    signal_lookup = (
        original[
            [
                "_TEMPORAL_ROW_ID",
                "_SIGNAL",
            ]
        ]
        .set_index("_TEMPORAL_ROW_ID")["_SIGNAL"]
    )

    data["_SIGNAL"] = (
        data["_TEMPORAL_ROW_ID"]
        .map(signal_lookup)
        .fillna(False)
        .astype(bool)
    )

    market = _normalise_market_data(market_dataframe)

    groups = {
        symbol: group.reset_index(drop=True)
        for symbol, group in data.groupby(
            "SYMBOL",
            sort=False,
        )
    }

    records: list[dict] = []
    unique_horizons = sorted(set(horizons))

    for symbol, group in groups.items():
    
        # Iterate only over rows selected for evaluation.
        # Original group indices are preserved, so `position`
        # remains valid for the future outcome lookup using iloc.
        selected_rows = group.loc[group["_SIGNAL"]]
    
        for position, row in selected_rows.iterrows():
    
            signal_date = row["TIMESTAMP"]

            if not (
                stage.start <= signal_date <= stage.end
            ):
                continue

            entry_price = float(row["CLOSE"])

            record = row.drop(
                labels=[
                    "_SIGNAL",
                    "_TEMPORAL_ROW_ID",
                ]
            ).to_dict()

            record.update(
                {
                    "STAGE": stage.name,
                    "SIGNAL_DATE": signal_date,
                    "ENTRY_DATE": signal_date,
                    "ENTRY_PRICE_BASIS": "CLOSE",
                    "ENTRY_PRICE": entry_price,
                    "ENTRY_STATUS": "COMPLETE",
                }
            )

            for horizon in unique_horizons:

                suffix = f"T{horizon}"

                outcome = None
                outcome_date = None
                outcome_price = None
                outcome_price_basis = None
                status = "COMPLETE"

                # Find the future session for this horizon.
                outcome_position = position + horizon

                if outcome_position >= len(group):

                    status = "OUTCOME_UNAVAILABLE"

                else:

                    outcome = group.iloc[outcome_position]
                    outcome_date = outcome["TIMESTAMP"]

                    if not (
                        stage.start <= outcome_date <= stage.end
                    ):
                        status = "OUTCOME_OUTSIDE_STAGE"

                    else:
                        outcome_price = float(
                            outcome["CLOSE"]
                        )
                        outcome_price_basis = (
                            "NEXT_SESSION_CLOSE"
                            if horizon == 1
                            else "CLOSE"
                        )

                eligible = (
                    status == "COMPLETE"
                    and outcome_price is not None
                    and entry_price > 0
                    and outcome_price > 0
                )

                if eligible:
                    stock_return = (
                        (outcome_price / entry_price) - 1
                    ) * 100
                else:
                    stock_return = None

                record.update(
                    {
                        f"HORIZON_{suffix}": horizon,
                        f"OUTCOME_DATE_{suffix}": outcome_date,
                        f"OUTCOME_PRICE_BASIS_{suffix}": (
                            outcome_price_basis
                        ),
                        f"OUTCOME_PRICE_{suffix}": outcome_price,
                        f"OUTCOME_ELIGIBLE_{suffix}": eligible,
                        f"OUTCOME_STATUS_{suffix}": status,
                        f"RETURN_{suffix}": stock_return,
                    }
                )

                # Benchmark returns use the same signal-date anchor
                # and close-to-close horizon.
                market_outcome = _market_outcome(
                    market=market,
                    signal_date=signal_date,
                    outcome_date=outcome_date,
                    stage=stage,
                )

                record.update(
                    {
                        f"MARKET_ENTRY_DATE_{suffix}": (
                            market_outcome["entry_date"]
                        ),
                        f"MARKET_OUTCOME_DATE_{suffix}": (
                            market_outcome["outcome_date"]
                        ),
                        f"MARKET_RETURN_{suffix}": (
                            market_outcome["return"]
                        ),
                        f"MARKET_OUTCOME_STATUS_{suffix}": (
                            market_outcome["status"]
                        ),
                    }
                )

                market_return = market_outcome["return"]

                record[f"EXCESS_RETURN_{suffix}"] = (
                    stock_return - market_return
                    if (
                        stock_return is not None
                        and market_return is not None
                    )
                    else None
                )

            records.append(record)

    if records:
        return pd.DataFrame(records)

    empty = (
        data
        .drop(
            columns=[
                "_SIGNAL",
                "_TEMPORAL_ROW_ID",
            ],
            errors="ignore",
        )
        .head(0)
        .copy()
    )

    for horizon in unique_horizons:

        suffix = f"T{horizon}"

        for column in (
            f"RETURN_{suffix}",
            f"MARKET_RETURN_{suffix}",
            f"EXCESS_RETURN_{suffix}",
        ):
            empty[column] = pd.Series(dtype="float64")

    return empty