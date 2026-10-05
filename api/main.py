"""
FastAPI entry point for the Research Cockpit.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date
from dotenv import load_dotenv

load_dotenv()

from fastapi.responses import StreamingResponse
from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from api.data.github_data import ResearchDataRepository

from api.schemas import (
    DateRangeResponse,
    HealthResponse,
)

from api.research.experiment_api import router as experiment_router
from api.research.workflow_api import router as workflow_router
from api.research.features import get_feature_registry
from api.research.universe import get_research_universe
from api.research.dataset import get_dataset_info
from api.research.models import ResearchRequest
from api.research.executor import execute_research
from api.research.job import (
    JobStatus,
    job_store,
)
from api.execution.router import router as execution_router
from api.research_agent.router import router as research_agent_router

# ======================================================================
# APPLICATION
# ======================================================================

app = FastAPI(
    title="Stock Scanner Research Cockpit API",
    version="0.1.0",
    description=(
        "Read-only research API backed by the "
        "STOCK_SCANNER_DATA GitHub repository."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(experiment_router)

app.include_router(workflow_router)

app.include_router(execution_router)

app.include_router(research_agent_router)

repository = ResearchDataRepository()

data_revision = repository.get_revision()
universe_revision = repository.get_file_revision(
    "research_universe.csv"
)

# ======================================================================
# SYSTEM
# ======================================================================

@app.get(
    "/",
    tags=["system"],
)
def root() -> dict[str, str]:
    return {
        "name": "Stock Scanner Research Cockpit API",
        "version": "0.1.0",
        "mode": "research-only",
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["system"],
)
def health() -> HealthResponse:

    status = repository.health()

    return HealthResponse(
        status=(
            "ok"
            if status["reachable"]
            else "error"
        ),
        data_repository=status["repository"],
        branch=status["branch"],
        data_repository_reachable=status["reachable"],
        error=status["error"],
    )


# ======================================================================
# DATA
# ======================================================================

@app.get(
    "/data/dates",
    response_model=DateRangeResponse,
    tags=["data"],
)
def available_dates() -> DateRangeResponse:

    try:

        dates = [
            date.fromisoformat(value)
            for value in repository.list_bhavcopy_dates()
        ]

    except RuntimeError as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    return DateRangeResponse(
        available_dates=dates,
    )


@app.get(
    "/data/bhavcopy",
    tags=["data"],
)
def bhavcopy(
    start_date: date = Query(...),
    end_date: date = Query(...),
    limit: int = Query(
        default=1000,
        ge=1,
        le=10000,
    ),
) -> dict:

    try:

        dataframe = repository.load_bhavcopy(
            start_date.isoformat(),
            end_date.isoformat(),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:

        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    if dataframe.empty:

        return {
            "start_date": start_date,
            "end_date": end_date,
            "rows": [],
            "total_rows": 0,
        }

    dataframe = (
        dataframe
        .head(limit)
        .copy()
    )

    dataframe = dataframe.where(
        dataframe.notna(),
        None,
    )

    return {
        "start_date": start_date,
        "end_date": end_date,
        "rows": dataframe.to_dict(
            orient="records"
        ),
        "total_rows": len(dataframe),
    }


# ======================================================================
# RESEARCH FEATURES
# ======================================================================

@app.get(
    "/research/features",
    tags=["research"],
)
def research_features() -> dict:

    return {
        "features": get_feature_registry(),
    }


# ======================================================================
# RESEARCH UNIVERSE
# ======================================================================

@app.get(
    "/research/universe",
    tags=["research"],
)
def research_universe() -> dict:

    return get_research_universe()


# ======================================================================
# RESEARCH DATASET INFORMATION
# ======================================================================

@app.get(
    "/research/dataset-info",
    tags=["research"],
)
def research_dataset_info(
    start_date: date,
    end_date: date,
) -> dict:

    if start_date > end_date:

        raise HTTPException(
            status_code=400,
            detail=(
                "start_date must be on or before "
                "end_date"
            ),
        )

    return get_dataset_info(
        start_date=start_date,
        end_date=end_date,
    )


# ======================================================================
# RESEARCH BACKGROUND EXECUTION
# ======================================================================

def run_research_background(
    job_id: str,
    request: ResearchRequest,
) -> None:

    try:

        job_store.update(
            job_id,
            status=JobStatus.RUNNING,
            progress=0,
            stage="Starting research",
        )

        def update_progress(
            progress: int,
            stage: str,
        ) -> None:

            job_store.update(
                job_id,
                status=JobStatus.RUNNING,
                progress=progress,
                stage=stage,
            )

        result = execute_research(
            request,
            repository=repository,
            progress_callback=update_progress,
        )

        job_store.update(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            stage="Research complete",
            result=result,
        )

    except HTTPException as exc:

        job_store.update(
            job_id,
            status=JobStatus.FAILED,
            stage="Research failed",
            progress=100,
            error=str(exc.detail),
        )

    except Exception as exc:

        job_store.update(
            job_id,
            status=JobStatus.FAILED,
            stage="Research failed",
            progress=100,
            error=str(exc),
        )

# ======================================================================
# RESEARCH RUN
# ======================================================================

@app.post(
    "/research/run",
)
def run_research_api(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
):

    job = job_store.create()

    background_tasks.add_task(
        run_research_background,
        job.job_id,
        request,
    )

    return {
        "job_id": job.job_id,
        "status": job.status.value,
        "progress": job.progress,
        "stage": job.stage,
    }


# ======================================================================
# RESEARCH JOB STATUS
# ======================================================================

@app.get(
    "/research/jobs/{job_id}",
    tags=["research"],
)
def research_job_status(
    job_id: str,
) -> dict:

    job = job_store.get(job_id)

    if job is None:

        raise HTTPException(
            status_code=404,
            detail="Research job not found.",
        )

    return job.to_dict()


# ======================================================================
# RESEARCH JOB STREAM
# ======================================================================

@app.get(
    "/research/jobs/{job_id}/stream",
    tags=["research"],
)
async def research_job_stream(
    job_id: str,
):

    job = job_store.get(job_id)

    if job is None:

        raise HTTPException(
            status_code=404,
            detail="Research job not found.",
        )

    async def event_stream():

        last_state = None

        while True:

            current_job = job_store.get(job_id)

            if current_job is None:
                yield (
                    "event: error\n"
                    'data: {"error":"Research job not found."}\n\n'
                )
                break

            current_state = current_job.to_dict()

            state_json = json.dumps(
                current_state,
                default=str,
            )

            if state_json != last_state:

                yield (
                    "event: progress\n"
                    f"data: {state_json}\n\n"
                )

                last_state = state_json

            if current_job.status in {
                JobStatus.COMPLETED,
                JobStatus.FAILED,
            }:
                break

            await asyncio.sleep(0.25)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )