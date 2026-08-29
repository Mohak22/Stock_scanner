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
        status="ok" if status["exists"] else "error",
        data_repository=status["data_repository"],
        data_repository_exists=status["exists"],
        processed_bhavcopy_exists=status["processed_bhavcopy_exists"],
        market_context_exists=status["market_context_exists"],
        historical_market_data_exists=status["historical_market_data_exists"],
        reference_data_exists=status["reference_data_exists"],
    )


@app.get("/data/dates", response_model=DateRangeResponse, tags=["data"])
def available_dates() -> DateRangeResponse:
    dates = [date.fromisoformat(value) for value in repository.list_bhavcopy_dates()]
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
