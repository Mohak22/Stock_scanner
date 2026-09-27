"""Post-strategy workflow.

Research evaluation ends when an experiment is locked and a strategy
version is created from that immutable evidence.

This module intentionally does not implement a second training /
validation / testing lifecycle.

Post-strategy lifecycle:

    LOCKED STRATEGY
        ↓
    FORWARD TESTING
        ↓
    DEPLOYMENT
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.research.experiment_api import (
    STRAT_PREFIX,
    GitHubStore,
    strategy_path,
)


router = APIRouter(
    prefix="/workflow",
    tags=["workflow"],
)

store = GitHubStore()

FORWARD_PREFIX = "research/forward_tests/"


class ForwardTestRequest(BaseModel):
    observation_date: str
    signal_count: int = Field(default=0, ge=0)
    notes: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


def now() -> str:
    return datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).isoformat()


def forward_test_id() -> str:
    return (
        f"FT-{datetime.now(ZoneInfo('Asia/Kolkata')):%Y%m%d-%H%M%S}"
        f"-{uuid4().hex[:6].upper()}"
    )


def forward_test_path(
    strategy_slug: str,
    version: int,
    test_id: str,
) -> str:
    return (
        f"{FORWARD_PREFIX}"
        f"{strategy_slug}/"
        f"v{version}/"
        f"{test_id}.json"
    )


def load_strategy(
    strategy_slug: str,
    version: int,
) -> tuple[dict, str]:
    try:
        return store.get(
            strategy_path(
                strategy_slug,
                version,
            )
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.get(
    "/strategies/{strategy_slug}/v{version}",
)
def get_workflow_status(
    strategy_slug: str,
    version: int,
) -> dict:
    strategy, _ = load_strategy(
        strategy_slug,
        version,
    )

    return {
        "strategy_slug": strategy_slug,
        "version": version,
        "strategy_name": strategy.get(
            "strategy_name"
        ),
        "strategy_status": strategy.get(
            "status"
        ),
        "lifecycle": [
            "LOCKED_STRATEGY",
            "FORWARD_TESTING",
            "DEPLOYMENT",
        ],
        "source_experiment_id": strategy.get(
            "source_experiment_id"
        ),
        "research_question": strategy.get(
            "research_question"
        ),
        "hypothesis": strategy.get(
            "hypothesis"
        ),
        "locked_at": strategy.get(
            "locked_at"
        ),
    }


@router.post(
    "/strategies/{strategy_slug}/v{version}/forward-test",
    status_code=201,
)
def record_forward_test(
    strategy_slug: str,
    version: int,
    request: ForwardTestRequest,
) -> dict:
    strategy, _ = load_strategy(
        strategy_slug,
        version,
    )

    if strategy.get("status") != "LOCKED":
        raise HTTPException(
            status_code=409,
            detail=(
                "Forward testing requires a LOCKED strategy."
            ),
        )

    test_id = forward_test_id()

    record = {
        "schema_version": 1,
        "forward_test_id": test_id,
        "created_at": now(),
        "strategy_slug": strategy_slug,
        "strategy_version": version,
        "source_experiment_id": strategy.get(
            "source_experiment_id"
        ),
        "observation_date": request.observation_date,
        "signal_count": request.signal_count,
        "notes": request.notes,
        "metrics": request.metrics,
        "strategy_snapshot": {
            "research_question": strategy.get(
                "research_question"
            ),
            "hypothesis": strategy.get(
                "hypothesis"
            ),
            "research_config": strategy.get(
                "research_config"
            ),
        },
    }

    try:
        commit_sha = store.put(
            forward_test_path(
                strategy_slug,
                version,
                test_id,
            ),
            record,
            (
                f"Record forward test "
                f"{strategy_slug} v{version} {test_id}"
            ),
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    return {
        **record,
        "commit_sha": commit_sha,
    }


@router.get(
    "/strategies/{strategy_slug}/v{version}/forward-tests",
)
def list_forward_tests(
    strategy_slug: str,
    version: int,
) -> dict:
    prefix = (
        f"{FORWARD_PREFIX}"
        f"{strategy_slug}/"
        f"v{version}/"
    )

    try:
        paths = [
            item["path"]
            for item in store.tree()
            if (
                item.get("type") == "blob"
                and item.get("path", "").startswith(prefix)
                and item.get("path", "").endswith(".json")
            )
        ]

        records = [
            store.get(path)[0]
            for path in paths
        ]
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    records.sort(
        key=lambda item: (
            item.get("observation_date") or "",
            item.get("created_at") or "",
        )
    )

    return {
        "count": len(records),
        "forward_tests": records,
    }
