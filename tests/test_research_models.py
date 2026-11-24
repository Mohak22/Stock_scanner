import pytest
from pydantic import ValidationError

from api.research.models import ResearchRequest
from api.research.models import UniverseConfig


def base_request(**overrides):
    payload = {
        "research_question": "Can a one-day spike persist?",
        "hypothesis": "A large one-day return may predict positive subsequent returns.",
        "development_start": "2016-01-01",
        "development_end": "2022-12-31",
        "validation_start": "2023-01-01",
        "validation_end": "2024-12-31",
        "holdout_start": "2025-01-01",
        "holdout_end": "2026-12-31",
        "universe": {"type": "all_stocks"},
        "features": [{"type": "return", "period": 1}],
        "entry_conditions": [
            {
                "feature": "return",
                "period": 1,
                "operator": ">=",
                "value": 5,
            }
        ],
        "evaluation_horizons": [1, 3, 5, 10],
    }
    payload.update(overrides)
    return payload


def test_canonical_research_request_is_valid():
    request = ResearchRequest(**base_request())

    assert request.development_start.isoformat() == "2016-01-01"
    assert request.holdout_end.isoformat() == "2026-12-31"
    assert request.evaluation_horizons == [1, 3, 5, 10]


def test_stage_overlap_is_rejected():
    with pytest.raises(ValidationError):
        ResearchRequest(
            **base_request(
                validation_start="2022-12-31"
            )
        )


def test_partial_validation_period_is_rejected():
    with pytest.raises(ValidationError):
        ResearchRequest(
            **base_request(
                validation_end=None
            )
        )


def test_partial_holdout_period_is_rejected():
    with pytest.raises(ValidationError):
        ResearchRequest(
            **base_request(
                holdout_start=None
            )
        )


def test_invalid_horizon_is_rejected():
    with pytest.raises(ValidationError):
        ResearchRequest(
            **base_request(
                evaluation_horizons=[1, 0, 5]
            )
        )


def test_outcome_definition_horizons_must_match():
    with pytest.raises(ValidationError):
        ResearchRequest(
            **base_request(
                outcome_definition={
                    "anchor": "entry_date",
                    "price_basis": "CLOSE",
                    "horizons": [1, 5],
                }
            )
        )


def test_all_stocks_defaults_to_point_in_time():
    config = UniverseConfig(type="all_stocks")
    assert config.membership_basis == "point_in_time"


def test_sector_defaults_to_current_snapshot():
    config = UniverseConfig(type="sector")
    assert config.membership_basis == "current_snapshot"


def test_point_in_time_rejects_current_constituent_universes():
    with pytest.raises(ValueError, match="only"):
        UniverseConfig(
            type="major_stocks",
            membership_basis="point_in_time",
        )


def test_nifty_50_defaults_to_current_snapshot():
    config = UniverseConfig(type="nifty_50")

    assert config.membership_basis == "current_snapshot"


def test_nifty_50_rejects_point_in_time_membership():
    with pytest.raises(ValueError, match="only"):
        UniverseConfig(
            type="nifty_50",
            membership_basis="point_in_time",
        )


def test_unsupported_universe_type_is_rejected():
    with pytest.raises(ValidationError):
        UniverseConfig(type="nifty_250")
