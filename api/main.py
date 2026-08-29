"""FastAPI entry point for the Research Cockpit."""

from __future__ import annotations

from datetime import date

from fastapi import FastAPI, HTTPException, Query

from api.data.github_data import ResearchDataRepository
from api.schemas import DateRangeResponse, HealthResponse


app = FastAPI(
    title="Stock Scanner Research Cockpit API",
    version="0.1.0",
    description=(
        "Read-only research API backed by the STOCK_SCANNER_DATA "
        "GitHub repository."
    ),
)

repository = ResearchDataRepository()


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {
        "name": "Stock Scanner Research Cockpit API",
        "version": "0.1.0",
        "mode": "research-only",
    }


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    status = repository.health()

    return HealthResponse(
        status="ok" if status["reachable"] else "error",
        data_repository=status["repository"],
        branch=status["branch"],
        data_repository_reachable=status["reachable"],
        error=status["error"],
    )


@app.get("/data/dates", response_model=DateRangeResponse, tags=["data"])
def available_dates() -> DateRangeResponse:
    try:
        dates = [
            date.fromisoformat(value)
            for value in repository.list_bhavcopy_dates()
        ]
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return DateRangeResponse(available_dates=dates)


@app.get("/data/bhavcopy", tags=["data"])
def bhavcopy(
    start_date: date = Query(...),
    end_date: date = Query(...),
    limit: int = Query(default=1000, ge=1, le=10000),
) -> dict:
    try:
        dataframe = repository.load_bhavcopy(
            start_date.isoformat(),
            end_date.isoformat(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if dataframe.empty:
        return {
            "start_date": start_date,
            "end_date": end_date,
            "rows": [],
            "total_rows": 0,
        }

    dataframe = dataframe.head(limit).copy()
    dataframe = dataframe.where(dataframe.notna(), None)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "rows": dataframe.to_dict(orient="records"),
        "total_rows": len(dataframe),
    }
