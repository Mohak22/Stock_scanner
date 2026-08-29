"""Pydantic schemas for the Research Cockpit API."""

from datetime import date

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    data_repository: str
    data_repository_exists: bool
    processed_bhavcopy_exists: bool
    market_context_exists: bool
    historical_market_data_exists: bool
    reference_data_exists: bool


class DateRangeResponse(BaseModel):
    available_dates: list[date]


class DataQuery(BaseModel):
    start_date: date
    end_date: date
    symbols: list[str] | None = Field(default=None)
