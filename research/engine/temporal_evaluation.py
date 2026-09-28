"""
Explicit, causal temporal evaluation for rule-based research.

Temporal convention
-------------------

Signal is observed at the close of signal_date.

The position is considered entered on the SAME DAY at the
signal-day closing price.

T+1 / BTST:
    Uses the next available trading session's HIGH multiplied
    by 0.985.

    This represents a theoretical BTST target 1.5% below the
    next trading day's high.

T+N for N > 1:
    Uses the close of the N-th subsequent available trading
    session after the signal date.

Example:

    Signal: 28 Sep
    Entry:  28 Sep CLOSE

    T+1: 29 Sep HIGH × 0.985
    T+3: third subsequent session CLOSE
    T+5: fifth subsequent session CLOSE
    T+10: tenth subsequent session CLOSE

Trading sessions are determined from the actual observations
available for each symbol. Weekends and exchange holidays
therefore do not count as horizons.

This is a research convention, not an executable-order claim.
The BTST T+1 value is a target-return measure because daily OHLC
data cannot prove that an intraday target order was actually
filled.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from research.engine.condition_engine import apply_conditions


BTST_TARGET_FACTOR = 0.985


TEMPORAL_CONVENTION = {
    "signal_observation": "signal_date close",
    "entry": "same signal_date close",
    "entry_price_basis": "CLOSE",
    "t1_outcome": (
        "next available symbol session HIGH multiplied by 0.985"
    ),
    "t1_outcome_price_basis": (
        "NEXT_SESSION_HIGH_MINUS_1_5_PERCENT"
    ),
    "t1_outcome_type": "theoretical_target_return",
    "outcome": (
        "N subsequent available symbol sessions after signal "
        "at close for N > 1"
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

        period = feature.get("period")

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

            required = 1

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

        elif feature_type == "return":

            if period is None:
                raise ValueError(
                    "return requires a period."
                )

            required = period + 1

        elif feature_type == "rsi":

            if period is None:
                raise ValueError(
                    "rsi requires a period."
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
    """Generate causal signals from a feature-enriched dataframe."""

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

    required = {
        "SYMBOL",
        "TIMESTAMP",
        "CLOSE",
        "HIGH",
    }

    missing = required - set(dataframe.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    data = dataframe.copy()

    data["_TEMPORAL_ROW_ID"] = range(
        len(data)
    )

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

    data["HIGH"] = pd.to_numeric(
        data["HIGH"],
        errors="coerce",
    )

    data["SYMBOL"] = (
        data["SYMBOL"]
        .astype(str)
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

    if market_dataframe is None:
        return None

    required = {
        "TIMESTAMP",
        "MARKET_CLOSE",
    }

    missing = required - set(
        market_dataframe.columns
    )

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

    return (
        market
        .dropna(
            subset=[
                "TIMESTAMP",
                "MARKET_CLOSE",
            ]
        )
        .sort_values("TIMESTAMP")
        .drop_duplicates(
            subset=["TIMESTAMP"],
            keep="last",
        )
        .reset_index(drop=True)
    )


def _market_outcome(
    market: pd.DataFrame | None,
    signal_date: pd.Timestamp | None,
    horizon: int,
    stage: TemporalStage,
) -> dict:

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

    signal_positions = market.index[
        market["TIMESTAMP"] >= signal_date
    ]

    if len(signal_positions) == 0:
        return {
            "entry_date": None,
            "outcome_date": None,
            "return": None,
            "status": "MARKET_ENTRY_UNAVAILABLE",
        }

    signal_position = int(
        signal_positions[0]
    )

    signal_row = market.iloc[
        signal_position
    ]

    outcome_position = (
        signal_position + horizon
    )

    if outcome_position >= len(market):
        return {
            "entry_date": signal_row["TIMESTAMP"],
            "outcome_date": None,
            "return": None,
            "status": "MARKET_OUTCOME_UNAVAILABLE",
        }

    outcome = market.iloc[
        outcome_position
    ]

    if not (
        stage.start
        <= outcome["TIMESTAMP"]
        <= stage.end
    ):

        return {
            "entry_date": signal_row["TIMESTAMP"],
            "outcome_date": outcome["TIMESTAMP"],
            "return": None,
            "status": "MARKET_OUTCOME_OUTSIDE_STAGE",
        }

    market_return = (
        (
            outcome["MARKET_CLOSE"]
            / signal_row["MARKET_CLOSE"]
        ) - 1
    ) * 100

    return {
        "entry_date": signal_row["TIMESTAMP"],
        "outcome_date": outcome["TIMESTAMP"],
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
    Evaluate one stage using signal-day entry.

    T+1:
        next available symbol session HIGH × 0.985.

    T+N for N > 1:
        N-th subsequent available symbol session CLOSE.

    Each horizon is independently eligible.

    Stage boundaries are strict:
        - signal must be inside stage
        - outcome must be inside stage

    The entry is the signal-day close, so there is no separate
    next-day entry row.
    """

    if (
        not horizons
        or any(
            int(horizon) <= 0
            for horizon in horizons
        )
    ):
        raise ValueError(
            "At least one positive horizon is required."
        )

    if len(signal_mask) != len(dataframe):
        raise ValueError(
            "signal_mask must align with dataframe rows."
        )

    original = dataframe.copy()

    original["_TEMPORAL_ROW_ID"] = range(
        len(original)
    )

    original["_SIGNAL"] = (
        signal_mask
        .fillna(False)
        .astype(bool)
        .to_numpy()
    )

    data = _normalise_stock_data(
        original
    )

    signal_lookup = (
        original[
            [
                "_TEMPORAL_ROW_ID",
                "_SIGNAL",
            ]
        ]
        .drop_duplicates(
            subset=["_TEMPORAL_ROW_ID"]
        )
        .set_index(
            "_TEMPORAL_ROW_ID"
        )["_SIGNAL"]
    )

    data["_SIGNAL"] = (
        data["_TEMPORAL_ROW_ID"]
        .map(signal_lookup)
        .fillna(False)
        .astype(bool)
    )

    market = _normalise_market_data(
        market_dataframe
    )

    groups = {
        symbol: group.reset_index(drop=True)
        for symbol, group
        in data.groupby(
            "SYMBOL",
            sort=False,
        )
    }

    records: list[dict] = []

    unique_horizons = sorted(
        set(
            int(value)
            for value in horizons
        )
    )

    for symbol, group in groups.items():

        for position, row in group.iterrows():

            signal_date = row["TIMESTAMP"]

            if not row["_SIGNAL"]:
                continue

            if not (
                stage.start
                <= signal_date
                <= stage.end
            ):
                continue

            signal_price = float(
                row["CLOSE"]
            )

            record = row.drop(
                labels=[
                    "_SIGNAL",
                    "_TEMPORAL_ROW_ID",
                ]
            ).to_dict()

            # --------------------------------------------------
            # ENTRY = SIGNAL-DAY CLOSE
            # --------------------------------------------------

            record.update(
                {
                    "STAGE": stage.name,
                    "SIGNAL_DATE": signal_date,
                    "ENTRY_DATE": signal_date,
                    "ENTRY_PRICE_BASIS": "CLOSE",
                    "ENTRY_PRICE": signal_price,
                    "ENTRY_STATUS": "COMPLETE",
                }
            )

            for horizon in unique_horizons:

                suffix = f"T{horizon}"

                outcome = None
                outcome_price = None
                outcome_price_basis = None
                status = "COMPLETE"

                # --------------------------------------------------
                # T+1 / BTST
                # --------------------------------------------------

                if horizon == 1:

                    outcome_position = (
                        position + 1
                    )

                    if (
                        outcome_position
                        >= len(group)
                    ):

                        status = (
                            "OUTCOME_UNAVAILABLE"
                        )

                    else:

                        outcome = group.iloc[
                            outcome_position
                        ]

                        outcome_date = (
                            outcome["TIMESTAMP"]
                        )

                        if not (
                            stage.start
                            <= outcome_date
                            <= stage.end
                        ):

                            status = (
                                "OUTCOME_OUTSIDE_STAGE"
                            )

                        elif pd.isna(
                            outcome["HIGH"]
                        ):

                            status = (
                                "OUTCOME_HIGH_UNAVAILABLE"
                            )

                        else:

                            next_day_high = float(
                                outcome["HIGH"]
                            )

                            outcome_price = (
                                next_day_high
                                * BTST_TARGET_FACTOR
                            )

                            outcome_price_basis = (
                                "NEXT_SESSION_HIGH_MINUS_1_5_PERCENT"
                            )

                # --------------------------------------------------
                # T+3 / T+5 / T+10 / any N > 1
                # --------------------------------------------------

                else:

                    outcome_position = (
                        position + horizon
                    )

                    if (
                        outcome_position
                        >= len(group)
                    ):

                        status = (
                            "OUTCOME_UNAVAILABLE"
                        )

                    else:

                        outcome = group.iloc[
                            outcome_position
                        ]

                        outcome_date = (
                            outcome["TIMESTAMP"]
                        )

                        if not (
                            stage.start
                            <= outcome_date
                            <= stage.end
                        ):

                            status = (
                                "OUTCOME_OUTSIDE_STAGE"
                            )

                        else:

                            outcome_price = float(
                                outcome["CLOSE"]
                            )

                            outcome_price_basis = (
                                "CLOSE"
                            )

                eligible = (
                    status == "COMPLETE"
                    and outcome_price is not None
                    and signal_price != 0
                )

                if eligible:

                    stock_return = (
                        (
                            outcome_price
                            / signal_price
                        ) - 1
                    ) * 100

                else:

                    stock_return = None

                outcome_date = (
                    outcome["TIMESTAMP"]
                    if outcome is not None
                    and status == "COMPLETE"
                    else (
                        outcome["TIMESTAMP"]
                        if outcome is not None
                        else None
                    )
                )

                record.update(
                    {
                        f"HORIZON_{suffix}": horizon,

                        f"OUTCOME_DATE_{suffix}": (
                            outcome_date
                        ),

                        f"OUTCOME_PRICE_BASIS_{suffix}": (
                            outcome_price_basis
                        ),

                        f"OUTCOME_PRICE_{suffix}": (
                            outcome_price
                        ),

                        f"OUTCOME_ELIGIBLE_{suffix}": (
                            eligible
                        ),

                        f"OUTCOME_STATUS_{suffix}": (
                            status
                        ),

                        f"RETURN_{suffix}": (
                            stock_return
                        ),
                    }
                )

                # --------------------------------------------------
                # MARKET BENCHMARK
                #
                # Market benchmark remains close-based from the
                # signal date because NIFTY does not participate
                # in the stock-specific BTST target convention.
                # --------------------------------------------------

                market_outcome = _market_outcome(
                    market=market,
                    signal_date=signal_date,
                    horizon=horizon,
                    stage=stage,
                )

                record.update(
                    {
                        f"MARKET_ENTRY_DATE_{suffix}": (
                            market_outcome[
                                "entry_date"
                            ]
                        ),

                        f"MARKET_OUTCOME_DATE_{suffix}": (
                            market_outcome[
                                "outcome_date"
                            ]
                        ),

                        f"MARKET_RETURN_{suffix}": (
                            market_outcome[
                                "return"
                            ]
                        ),

                        f"MARKET_OUTCOME_STATUS_{suffix}": (
                            market_outcome[
                                "status"
                            ]
                        ),
                    }
                )

                market_return = (
                    market_outcome["return"]
                )

                record[
                    f"EXCESS_RETURN_{suffix}"
                ] = (
                    stock_return
                    - market_return
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

            empty[column] = pd.Series(
                dtype="float64"
            )

    return empty