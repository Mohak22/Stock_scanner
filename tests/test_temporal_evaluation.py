from __future__ import annotations

import pandas as pd
import pytest

from research.engine.feature_engine import calculate_features
from research.engine.temporal_evaluation import (
    TEMPORAL_CONVENTION,
    TemporalStage,
    evaluate_temporal_stage,
    generate_signal_mask,
)


def stock_data(dates, closes=None, symbol="ABC"):
    if closes is None:
        closes = list(range(100, 100 + len(dates)))
    return pd.DataFrame({"SYMBOL": symbol, "TIMESTAMP": pd.to_datetime(dates), "CLOSE": closes})


def all_signals(data):
    return generate_signal_mask(data, [{"feature": "close", "operator": ">=", "value": 0}])


def record_for(result, date):
    return result.loc[result["SIGNAL_DATE"] == pd.Timestamp(date)].iloc[0]


def test_normal_signal_has_traceable_complete_outcomes():
    dates = pd.bdate_range("2022-01-03", periods=8)
    data = stock_data(dates)
    result = evaluate_temporal_stage(data, all_signals(data), TemporalStage.create("development", dates[0], dates[-1]), [1, 3])
    row = record_for(result, dates[0])

    assert row["ENTRY_DATE"] == dates[1]
    assert row["OUTCOME_DATE_T1"] == dates[2]
    assert row["OUTCOME_DATE_T3"] == dates[4]
    assert row["OUTCOME_ELIGIBLE_T1"]
    assert row["OUTCOME_ELIGIBLE_T3"]
    assert row["RETURN_T1"] == pytest.approx((102 / 101 - 1) * 100)
    assert TEMPORAL_CONVENTION["horizon_anchor"] == "entry_date"


def test_t1_crossing_development_boundary_is_explicitly_ineligible():
    dates = pd.bdate_range("2022-12-26", periods=7)
    data = stock_data(dates)
    stage = TemporalStage.create("development", dates[0], dates[3])
    row = record_for(evaluate_temporal_stage(data, all_signals(data), stage, [1]), dates[2])

    assert row["ENTRY_DATE"] == dates[3]
    assert row["OUTCOME_DATE_T1"] == dates[4]
    assert not row["OUTCOME_ELIGIBLE_T1"]
    assert row["OUTCOME_STATUS_T1"] == "OUTCOME_OUTSIDE_STAGE"
    assert pd.isna(row["RETURN_T1"])


def test_t5_crossing_development_boundary_is_explicitly_ineligible():
    dates = pd.bdate_range("2022-12-20", periods=9)
    data = stock_data(dates)
    stage = TemporalStage.create("development", dates[0], dates[5])
    row = record_for(evaluate_temporal_stage(data, all_signals(data), stage, [5]), dates[0])

    assert row["OUTCOME_DATE_T5"] == dates[6]
    assert row["OUTCOME_STATUS_T5"] == "OUTCOME_OUTSIDE_STAGE"
    assert not row["OUTCOME_ELIGIBLE_T5"]


def test_t10_crossing_validation_boundary_is_explicitly_ineligible():
    dates = pd.bdate_range("2024-12-02", periods=14)
    data = stock_data(dates)
    stage = TemporalStage.create("validation", dates[0], dates[11])
    row = record_for(evaluate_temporal_stage(data, all_signals(data), stage, [10]), dates[1])

    assert row["OUTCOME_DATE_T10"] == dates[12]
    assert row["OUTCOME_STATUS_T10"] == "OUTCOME_OUTSIDE_STAGE"


def test_horizons_are_independently_eligible():
    dates = pd.bdate_range("2023-01-02", periods=8)
    data = stock_data(dates)
    stage = TemporalStage.create("development", dates[0], dates[3])
    row = record_for(evaluate_temporal_stage(data, all_signals(data), stage, [1, 5]), dates[0])

    assert row["OUTCOME_ELIGIBLE_T1"]
    assert not row["OUTCOME_ELIGIBLE_T5"]
    assert row["OUTCOME_STATUS_T5"] == "OUTCOME_OUTSIDE_STAGE"


def test_missing_symbol_sessions_use_next_available_symbol_observation():
    dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-08", "2024-01-09"])
    data = stock_data(dates)
    row = record_for(
        evaluate_temporal_stage(data, all_signals(data), TemporalStage.create("development", dates[0], dates[-1]), [1]),
        dates[0],
    )

    assert row["ENTRY_DATE"] == dates[1]
    assert row["OUTCOME_DATE_T1"] == dates[2]
    assert row["OUTCOME_DATE_T1"] > row["ENTRY_DATE"]


def test_entry_and_outcome_dates_follow_signal_in_order():
    dates = pd.bdate_range("2024-02-01", periods=5)
    data = stock_data(dates)
    row = record_for(
        evaluate_temporal_stage(data, all_signals(data), TemporalStage.create("development", dates[0], dates[-1]), [1]),
        dates[0],
    )

    assert row["SIGNAL_DATE"] < row["ENTRY_DATE"] < row["OUTCOME_DATE_T1"]


def test_future_data_does_not_change_prior_signal_or_feature_value():
    dates = pd.bdate_range("2024-03-01", periods=7)
    original = stock_data(dates, [100, 101, 102, 103, 104, 105, 106])
    changed = original.copy()
    changed.loc[changed.index >= 5, "CLOSE"] = [1000, 1]

    original_features = calculate_features(original, [{"type": "return", "period": 1}])
    changed_features = calculate_features(changed, [{"type": "return", "period": 1}])
    condition = [{"feature": "return", "period": 1, "operator": ">", "value": 0}]

    assert original_features.loc[4, "RETURN_1"] == changed_features.loc[4, "RETURN_1"]
    assert generate_signal_mask(original_features, condition).iloc[:5].equals(
        generate_signal_mask(changed_features, condition).iloc[:5]
    )


def test_feature_warmup_does_not_create_early_signal():
    dates = pd.bdate_range("2024-04-01", periods=5)
    features = calculate_features(stock_data(dates), [{"type": "sma", "period": 3}])
    mask = generate_signal_mask(features, [{"feature": "sma", "period": 3, "operator": ">", "value": 0}])

    assert not mask.iloc[0]
    assert not mask.iloc[1]
    assert mask.iloc[2]


def test_benchmark_uses_entry_anchored_market_dates():
    dates = pd.bdate_range("2024-05-01", periods=6)
    data = stock_data(dates)
    market = pd.DataFrame({"TIMESTAMP": dates, "MARKET_CLOSE": [200, 202, 204, 206, 208, 210]})
    row = record_for(
        evaluate_temporal_stage(data, all_signals(data), TemporalStage.create("development", dates[0], dates[-1]), [1], market),
        dates[0],
    )

    assert row["MARKET_ENTRY_DATE_T1"] == dates[1]
    assert row["MARKET_OUTCOME_DATE_T1"] == dates[2]
    assert row["MARKET_OUTCOME_STATUS_T1"] == "COMPLETE"
    assert row["MARKET_RETURN_T1"] == pytest.approx((204 / 202 - 1) * 100)


def test_temporal_evaluation_has_no_2025_cutoff():
    dates = pd.bdate_range("2026-01-05", periods=5)
    data = stock_data(dates)
    row = record_for(
        evaluate_temporal_stage(data, all_signals(data), TemporalStage.create("final_holdout", dates[0], dates[-1]), [1]),
        dates[0],
    )

    assert row["STAGE"] == "final_holdout"
    assert row["OUTCOME_ELIGIBLE_T1"]
