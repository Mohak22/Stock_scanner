"""Explicit, causal temporal evaluation for rule-based research.

Phase 1 convention
------------------
Signals are observed at the *close* of ``signal_date`` because current
features and conditions may use that close.  A signal therefore cannot be
executed on that same close.  The simulated entry is the next available row
for that symbol, at that row's close.  ``T+N`` is the close-to-close return
from this entry close to the close N subsequent available symbol sessions
later.

This is an evaluation convention, not a claim about executable orders.  The
result records all dates and price bases so a future execution model can
replace it without ambiguity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

from research.engine.condition_engine import apply_conditions


TEMPORAL_CONVENTION = {
    "signal_observation": "signal_date close",
    "entry": "next available symbol session close",
    "entry_price_basis": "CLOSE",
    "outcome": "N available symbol sessions after entry, at close",
    "outcome_price_basis": "CLOSE",
    "horizon_anchor": "entry_date",
    "stage_boundary_policy": "strict_signal_entry_and_outcome_within_stage",
}


@dataclass(frozen=True)
class TemporalStage:
    """Inclusive signal, entry, and outcome date window for one stage."""

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
            raise ValueError("Stage start must be on or before stage end.")
        return cls(name=name, start=start_value, end=end_value)


def feature_lookback_requirements(features: Iterable[dict]) -> dict[str, int]:
    """Return minimum prior/total observations required by current features.

    Values are deliberately observation counts, not calendar-day estimates.
    EMA is causal from its first observation, while SMA/averages require a
    complete window and RSI requires the period changes plus its initial row.
    """

    requirements: dict[str, int] = {}
    for feature in features:
        feature_type = str(feature.get("type", "")).lower()
        period = feature.get("period")
        if feature_type in {"open", "high", "low", "close", "volume", "delivery_percentage", "delivery_quantity"}:
            required = 1
        elif feature_type == "ema":
            required = 1
        elif feature_type in {"sma", "average_volume", "average_delivery_percentage", "volume_average", "delivery_percentage_average"}:
            required = int(period)
        elif feature_type == "return":
            required = int(period) + 1
        elif feature_type == "rsi":
            required = int(period) + 1
        else:
            # The feature engine remains the authority for support/validation.
            continue

        if required <= 0:
            raise ValueError(f"Feature lookback must be positive: {feature}")
        key = f"{feature_type}:{period}" if period is not None else feature_type
        requirements[key] = required
    return requirements


def generate_signal_mask(dataframe: pd.DataFrame, conditions: list[dict]) -> pd.Series:
    """Generate causal signals from an already feature-enriched dataframe."""

    signal_mask = apply_conditions(dataframe, conditions)
    return signal_mask.fillna(False).astype(bool)


def _normalise_stock_data(dataframe: pd.DataFrame) -> pd.DataFrame:
    required = {"SYMBOL", "TIMESTAMP", "CLOSE"}
    missing = required - set(dataframe.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    data = dataframe.copy()
    data["TIMESTAMP"] = pd.to_datetime(data["TIMESTAMP"], errors="coerce").dt.normalize()
    data["CLOSE"] = pd.to_numeric(data["CLOSE"], errors="coerce")
    data["SYMBOL"] = data["SYMBOL"].astype(str).str.strip().str.upper()
    data = data.dropna(subset=["SYMBOL", "TIMESTAMP", "CLOSE"])
    data = data.sort_values(["SYMBOL", "TIMESTAMP"]).drop_duplicates(
        subset=["SYMBOL", "TIMESTAMP"], keep="last"
    ).reset_index(drop=True)
    return data


def _normalise_market_data(market_dataframe: pd.DataFrame | None) -> pd.DataFrame | None:
    if market_dataframe is None:
        return None
    required = {"TIMESTAMP", "MARKET_CLOSE"}
    missing = required - set(market_dataframe.columns)
    if missing:
        raise ValueError(f"Market data missing columns: {sorted(missing)}")
    market = market_dataframe.copy()
    market["TIMESTAMP"] = pd.to_datetime(market["TIMESTAMP"], errors="coerce").dt.normalize()
    market["MARKET_CLOSE"] = pd.to_numeric(market["MARKET_CLOSE"], errors="coerce")
    return market.dropna(subset=["TIMESTAMP", "MARKET_CLOSE"]).sort_values("TIMESTAMP").drop_duplicates(
        subset=["TIMESTAMP"], keep="last"
    ).reset_index(drop=True)


def _market_outcome(
    market: pd.DataFrame | None,
    entry_date: pd.Timestamp | None,
    horizon: int,
    stage: TemporalStage,
) -> dict:
    if market is None or entry_date is None:
        return {"entry_date": None, "outcome_date": None, "return": None, "status": "MARKET_DATA_UNAVAILABLE"}
    entry_positions = market.index[market["TIMESTAMP"] >= entry_date]
    if len(entry_positions) == 0:
        return {"entry_date": None, "outcome_date": None, "return": None, "status": "MARKET_ENTRY_UNAVAILABLE"}
    entry_position = int(entry_positions[0])
    market_entry = market.iloc[entry_position]
    outcome_position = entry_position + horizon
    if outcome_position >= len(market):
        return {"entry_date": market_entry["TIMESTAMP"], "outcome_date": None, "return": None, "status": "MARKET_OUTCOME_UNAVAILABLE"}
    outcome = market.iloc[outcome_position]
    if not (stage.start <= outcome["TIMESTAMP"] <= stage.end):
        return {"entry_date": market_entry["TIMESTAMP"], "outcome_date": outcome["TIMESTAMP"], "return": None, "status": "MARKET_OUTCOME_OUTSIDE_STAGE"}
    return {
        "entry_date": market_entry["TIMESTAMP"],
        "outcome_date": outcome["TIMESTAMP"],
        "return": ((outcome["MARKET_CLOSE"] / market_entry["MARKET_CLOSE"]) - 1) * 100,
        "status": "COMPLETE",
    }


def evaluate_temporal_stage(
    dataframe: pd.DataFrame,
    signal_mask: pd.Series,
    stage: TemporalStage,
    horizons: list[int],
    market_dataframe: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Evaluate one stage with strict per-horizon boundary eligibility.

    Candidate signals are retained when their signal date is in the stage.
    Each horizon independently records an outcome date, return, eligibility,
    and reason.  A boundary-incomplete horizon has a null return; it is never
    silently truncated or allowed to consume another stage's outcome.
    """

    if not horizons or any(int(horizon) <= 0 for horizon in horizons):
        raise ValueError("At least one positive horizon is required.")
    data = _normalise_stock_data(dataframe)
    market = _normalise_market_data(market_dataframe)
    # The caller normally passes a mask produced from the same sorted frame.
    # Preserve position only when index identity survived normalization.
    if len(signal_mask) != len(dataframe):
        raise ValueError("signal_mask must align with dataframe rows.")
    data["_SIGNAL"] = pd.Series(signal_mask.to_numpy(), index=data.index).fillna(False).astype(bool)

    groups = {symbol: group.reset_index(drop=True) for symbol, group in data.groupby("SYMBOL", sort=False)}
    records: list[dict] = []
    for symbol, group in groups.items():
        for position, row in group.iterrows():
            if not row["_SIGNAL"] or not (stage.start <= row["TIMESTAMP"] <= stage.end):
                continue
            record = row.drop(labels=["_SIGNAL"]).to_dict()
            signal_date = row["TIMESTAMP"]
            entry_position = position + 1
            entry = group.iloc[entry_position] if entry_position < len(group) else None
            entry_date = entry["TIMESTAMP"] if entry is not None else None
            entry_status = "COMPLETE"
            if entry is None:
                entry_status = "ENTRY_UNAVAILABLE"
            elif not (stage.start <= entry_date <= stage.end):
                entry_status = "ENTRY_OUTSIDE_STAGE"

            record.update({
                "STAGE": stage.name,
                "SIGNAL_DATE": signal_date,
                "ENTRY_DATE": entry_date,
                "ENTRY_PRICE_BASIS": "CLOSE",
                "ENTRY_PRICE": float(entry["CLOSE"]) if entry is not None else None,
                "ENTRY_STATUS": entry_status,
            })
            for horizon_value in sorted(set(int(value) for value in horizons)):
                suffix = f"T{horizon_value}"
                outcome = None
                status = entry_status
                if entry is not None and entry_status == "COMPLETE":
                    outcome_position = entry_position + horizon_value
                    if outcome_position >= len(group):
                        status = "OUTCOME_UNAVAILABLE"
                    else:
                        outcome = group.iloc[outcome_position]
                        if not (stage.start <= outcome["TIMESTAMP"] <= stage.end):
                            status = "OUTCOME_OUTSIDE_STAGE"
                        else:
                            status = "COMPLETE"

                eligible = status == "COMPLETE"
                outcome_date = outcome["TIMESTAMP"] if outcome is not None else None
                outcome_price = float(outcome["CLOSE"]) if eligible else None
                stock_return = (
                    ((outcome_price / record["ENTRY_PRICE"]) - 1) * 100
                    if eligible and record["ENTRY_PRICE"] not in {None, 0}
                    else None
                )
                record.update({
                    f"HORIZON_{suffix}": horizon_value,
                    f"OUTCOME_DATE_{suffix}": outcome_date,
                    f"OUTCOME_PRICE_BASIS_{suffix}": "CLOSE",
                    f"OUTCOME_PRICE_{suffix}": outcome_price,
                    f"OUTCOME_ELIGIBLE_{suffix}": eligible,
                    f"OUTCOME_STATUS_{suffix}": status,
                    f"RETURN_{suffix}": stock_return,
                })
                market_outcome = _market_outcome(market, entry_date, horizon_value, stage)
                record.update({
                    f"MARKET_ENTRY_DATE_{suffix}": market_outcome["entry_date"],
                    f"MARKET_OUTCOME_DATE_{suffix}": market_outcome["outcome_date"],
                    f"MARKET_RETURN_{suffix}": market_outcome["return"],
                    f"MARKET_OUTCOME_STATUS_{suffix}": market_outcome["status"],
                })
                record[f"EXCESS_RETURN_{suffix}"] = (
                    stock_return - market_outcome["return"]
                    if stock_return is not None and market_outcome["return"] is not None
                    else None
                )
            records.append(record)

    if records:
        return pd.DataFrame(records)

    # Keep downstream diagnostics stable even when a stage has no signals.
    empty = data.drop(columns=["_SIGNAL"]).head(0).copy()
    for horizon_value in sorted(set(int(value) for value in horizons)):
        suffix = f"T{horizon_value}"
        for column in (
            f"RETURN_{suffix}",
            f"MARKET_RETURN_{suffix}",
            f"EXCESS_RETURN_{suffix}",
        ):
            empty[column] = pd.Series(dtype="float64")
    return empty
