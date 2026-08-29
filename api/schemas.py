"""Pydantic schemas for the Research Cockpit API."""

from datetime import date

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    data_repository: str
    branch: str
    data_repository_reachable: bool
    error: str | None = None


class DateRangeResponse(BaseModel):
    available_dates: list[date]


class DataQuery(BaseModel):
    start_date: date
    end_date: date
    symbols: list[str] | None = Field(default=None)
