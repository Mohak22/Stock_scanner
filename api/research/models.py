from datetime import date

from pydantic import BaseModel, Field, model_validator


class UniverseConfig(BaseModel):
    type: str = "all_stocks"
    value: str | None = None
    symbols: list[str] = Field(default_factory=list)

    membership_basis: str = "current_snapshot"

    @model_validator(mode="after")
    def validate_membership_basis(self):

        allowed = {
            "current_snapshot",
            "point_in_time",
        }

        if self.membership_basis not in allowed:
            raise ValueError(
                "membership_basis must be either "
                "'current_snapshot' or 'point_in_time'."
            )

        return self

class FeatureConfig(BaseModel):
    type: str
    period: int | None = None


class ConditionConfig(BaseModel):
    feature: str
    period: int | None = None
    operator: str
    value: int | float | str


class SignalTimingConfig(BaseModel):
    observation: str = "signal_date_close"
    entry: str = "next_available_symbol_session_close"
    price_basis: str = "CLOSE"


class OutcomeDefinition(BaseModel):
    anchor: str = "entry_date"
    price_basis: str = "CLOSE"
    horizons: list[int] = Field(default_factory=lambda: [1, 3, 5, 10])


class ResearchRequest(BaseModel):
    development_start: date
    development_end: date

    validation_start: date | None = None
    validation_end: date | None = None

    holdout_start: date | None = None
    holdout_end: date | None = None

    universe: UniverseConfig
    features: list[FeatureConfig]
    entry_conditions: list[ConditionConfig]

    evaluation_horizons: list[int] = Field(
        default_factory=lambda: [1, 3, 5, 10]
    )

    signal_timing: SignalTimingConfig = Field(
        default_factory=SignalTimingConfig
    )

    outcome_definition: OutcomeDefinition | None = None

    @model_validator(mode="after")
    def validate_temporal_contract(self):
        if self.development_start > self.development_end:
            raise ValueError(
                "Development start date must be before development end date."
            )

        if (self.validation_start is None) != (
            self.validation_end is None
        ):
            raise ValueError(
                "Validation start and end dates must be provided together."
            )

        if (self.holdout_start is None) != (
            self.holdout_end is None
        ):
            raise ValueError(
                "Final holdout start and end dates must be provided together."
            )

        stages = [
            ("development", self.development_start, self.development_end),
        ]

        if self.validation_start is not None:
            stages.append(
                (
                    "validation",
                    self.validation_start,
                    self.validation_end,
                )
            )

        if self.holdout_start is not None:
            stages.append(
                (
                    "final_holdout",
                    self.holdout_start,
                    self.holdout_end,
                )
            )

        previous_name, _, previous_end = stages[0]

        for name, start, end in stages[1:]:
            if start <= previous_end:
                raise ValueError(
                    f"{name.title()} must start after {previous_name} ends."
                )
            if start > end:
                raise ValueError(
                    f"{name.title()} start date must be before its end date."
                )
            previous_name = name
            previous_end = end

        if not self.evaluation_horizons:
            raise ValueError(
                "At least one evaluation horizon is required."
            )

        if any(
            int(horizon) <= 0
            for horizon in self.evaluation_horizons
        ):
            raise ValueError(
                "Evaluation horizons must be positive integers."
            )

        if self.outcome_definition is not None:
            if self.outcome_definition.horizons:
                if set(
                    self.outcome_definition.horizons
                ) != set(self.evaluation_horizons):
                    raise ValueError(
                        "Outcome-definition horizons must match evaluation_horizons."
                    )

        return self
