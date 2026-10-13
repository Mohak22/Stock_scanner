
from datetime import date
from typing import Any, Literal
import math
from pydantic import BaseModel, Field, model_validator
from api.research.features import normalize_feature_parameters


class UniverseConfig(BaseModel):
    type: str = "all_stocks"
    value: str | None = None
    symbols: list[str] = Field(default_factory=list)
    membership_basis: str | None = None

    @model_validator(mode="after")
    def validate_membership_basis(self):
        # Make the safer choice the default for broad historical
        # research, while retaining explicit snapshot mode.
        if self.membership_basis is None:
            self.membership_basis = (
                "point_in_time"
                if self.type == "all_stocks"
                else "current_snapshot"
            )

        if self.membership_basis not in {
            "current_snapshot",
            "point_in_time",
        }:
            raise ValueError(
                "membership_basis must be either "
                "'current_snapshot' or 'point_in_time'."
            )

        if (
            self.membership_basis == "point_in_time"
            and self.type != "all_stocks"
        ):
            raise ValueError(
                "Point-in-time membership is currently supported "
                "only for the 'all_stocks' universe. Historical "
                "sector classifications and historical index "
                "constituents are not yet available."
            )

        return self

class FeatureConfig(BaseModel):
    type: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_period(cls,data):
        if not isinstance(data,dict): return data
        p=dict(data); params=dict(p.get("parameters") or {})
        if "period" in p and "period" not in params: params["period"]=p["period"]
        p["parameters"]=params; p.pop("period",None); return p
    @model_validator(mode="after")
    def validate_parameters(self):
        self.parameters=normalize_feature_parameters(self.type,self.parameters); return self

class ExpressionConfig(BaseModel):
    feature: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)
    value: int | float | str | None = None
    multiplier: float = 1.0
    @model_validator(mode="before")
    @classmethod
    def normalize_expression(cls,data):
        if not isinstance(data,dict): return {"value":data}
        p=dict(data); params=dict(p.get("parameters") or {})
        if "period" in p and "period" not in params: params["period"]=p["period"]
        p["parameters"]=params; p.pop("period",None); return p
    @model_validator(mode="after")
    def validate_expression(self):
        has_feature=bool(self.feature); has_value=self.value is not None
        if has_feature == has_value: raise ValueError("An expression must contain exactly one of 'feature' or 'value'.")
        if not math.isfinite(float(self.multiplier)) or self.multiplier < 0:
            raise ValueError("Expression multiplier must be finite and non-negative.")
        if has_feature: self.parameters=normalize_feature_parameters(self.feature,self.parameters)
        elif self.parameters: raise ValueError("Value expressions cannot contain feature parameters.")
        return self

class ConditionConfig(BaseModel):
    left: ExpressionConfig
    operator: Literal["<","<=",">",">=","==","!="]
    right: ExpressionConfig
    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_condition(cls,data):
        if not isinstance(data,dict) or ("left" in data and "right" in data): return data
        p=dict(data); lp={}
        if p.get("period") not in (None,""): lp["period"]=p["period"]
        rv=p.get("value")
        if isinstance(rv,dict): right=dict(rv)
        elif isinstance(rv,str): right={"feature":rv}
        else: right={"value":rv}
        if "period" in right and "parameters" not in right:
            right["parameters"]={"period":right.pop("period")}
        return {"left":{"feature":p.get("feature"),"parameters":lp},"operator":p.get("operator"),"right":right}


class SignalTimingConfig(BaseModel):
    """Fixed temporal convention used by the research evaluator."""

    observation: Literal["signal_date_close"] = "signal_date_close"
    entry: Literal["same_signal_date_close_proxy"] = (
        "same_signal_date_close_proxy"
    )
    price_basis: Literal["CLOSE"] = "CLOSE"


class OutcomeDefinition(BaseModel):
    """Forward outcomes are measured from the signal-date close proxy."""

    anchor: Literal["signal_date"] = "signal_date"
    price_basis: Literal["CLOSE"] = "CLOSE"
    horizons: list[int] = Field(
        default_factory=lambda: [1, 3, 5, 10]
    )


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
    evaluation_horizons: list[int] = Field(default_factory=lambda:[1,3,5,10])
    signal_timing: SignalTimingConfig = Field(default_factory=SignalTimingConfig)
    outcome_definition: OutcomeDefinition | None = None
    @model_validator(mode="after")
    def validate_temporal_contract(self):
        if self.development_start > self.development_end: raise ValueError("Development start date must be before development end date.")
        if (self.validation_start is None)!=(self.validation_end is None): raise ValueError("Validation start and end dates must be provided together.")
        if (self.holdout_start is None)!=(self.holdout_end is None): raise ValueError("Final holdout start and end dates must be provided together.")
        stages=[("development",self.development_start,self.development_end)]
        if self.validation_start is not None: stages.append(("validation",self.validation_start,self.validation_end))
        if self.holdout_start is not None: stages.append(("final_holdout",self.holdout_start,self.holdout_end))
        prev_name,_,prev_end=stages[0]
        for name,start,end in stages[1:]:
            if start<=prev_end: raise ValueError(f"{name.title()} must start after {prev_name} ends.")
            if start>end: raise ValueError(f"{name.title()} start date must be before its end date.")
            prev_name,prev_end=name,end
        if not self.evaluation_horizons or any(int(h)<=0 for h in self.evaluation_horizons): raise ValueError("Evaluation horizons must be positive integers.")
        if self.outcome_definition and self.outcome_definition.horizons and set(self.outcome_definition.horizons)!=set(self.evaluation_horizons):
            raise ValueError("Outcome-definition horizons must match evaluation_horizons.")
        return self
