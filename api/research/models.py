# -*- coding: utf-8 -*-
"""
Created on Sun Aug 30 14:34:05 2026

@author: mohak
"""

"""
Research API Request Models

These Pydantic models define the contract between:

    React Strategy Inventor
            ↓
        FastAPI

They describe WHAT the user wants to research.

They do not execute the research.
"""

from datetime import date

from pydantic import BaseModel, Field


class UniverseConfig(BaseModel):
    type: str = "all_stocks"
    symbols: list[str] = []


class FeatureConfig(BaseModel):
    type: str
    period: int | None = None


class ConditionConfig(BaseModel):
    feature: str
    operator: str
    value: int | float | str


class ResearchRequest(BaseModel):

    training_start: date
    training_end: date

    validation_start: date | None = None
    validation_end: date | None = None

    testing_start: date | None = None
    testing_end: date | None = None

    universe: UniverseConfig

    features: list[FeatureConfig]

    entry_conditions: list[ConditionConfig]

    evaluation_horizons: list[int] = Field(
        default=[1, 3, 5, 10]
    )