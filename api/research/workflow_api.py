"""Post-strategy lifecycle.

Research evaluation ends when an experiment is locked and a strategy
version is created from that immutable evidence.

Post-strategy lifecycle:

    LOCKED STRATEGY
        ↓
    FORWARD TESTING
        ↓
    DEPLOYMENT

Forward testing is deliberately separated from historical research.
It records observations made after the strategy's research holdout and
always carries the frozen strategy identity with the observation.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from api.research.experiment_api import (
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
    signals: list[dict[str, Any]] = Field(default_factory=list)
    outcomes: list[dict[str, Any]] = Field(default_factory=list)
    market_context: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)

    @field_validator("observation_date")
    @classmethod
    def validate_observation_date(cls, value: str) -> str:
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(
                "observation_date must use YYYY-MM-DD format."
            ) from exc

        return value


def now() -> str:
    return datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).isoformat()


def today() -> str:
    return datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).date().isoformat()


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


def _stable_hash(document: dict) -> str:
    payload = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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


def strategy_snapshot(strategy: dict) -> dict:
    snapshot = strategy.get("snapshot")

    if isinstance(snapshot, dict) and snapshot:
        return snapshot

    # Backward-compatible fallback for pre-Phase-5 strategies.
    return {
        "source_experiment_id": strategy.get(
            "source_experiment_id"
        ),
        "source_experiment_sha": strategy.get(
            "source_experiment_sha"
        ),
        "source_experiment_locked_at": strategy.get(
            "source_experiment_locked_at"
        ),
        "research_question": strategy.get(
            "research_question"
        ),
        "hypothesis": strategy.get("hypothesis"),
        "research_config": strategy.get(
            "research_config", {}
        ),
        "evaluation_evidence": strategy.get(
            "evaluation_evidence", {}
        ),
    }


def strategy_fingerprint(strategy: dict) -> str:
    existing = strategy.get("strategy_fingerprint")

    if existing:
        return str(existing)

    return _stable_hash(strategy_snapshot(strategy))


def _holdout_end(strategy: dict) -> str | None:
    config = strategy.get("research_config", {})
    if not isinstance(config, dict):
        return None

    value = config.get("holdout_end")
    if value:
        return str(value)

    return None


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
        "strategy_fingerprint": strategy_fingerprint(
            strategy
        ),
        "locked_at": strategy.get(
            "locked_at"
        ),
        "holdout_end": _holdout_end(strategy),
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

    if request.observation_date > today():
        raise HTTPException(
            status_code=400,
            detail="Forward-test observation_date cannot be in the future.",
        )

    holdout_end = _holdout_end(strategy)

    if holdout_end and request.observation_date <= holdout_end:
        raise HTTPException(
            status_code=409,
            detail=(
                "Forward-test observation_date must be after the "
                f"strategy research holdout_end ({holdout_end})."
            ),
        )

    prefix = (
        f"{FORWARD_PREFIX}"
        f"{strategy_slug}/"
        f"v{version}/"
    )

    try:
        existing_paths = [
            item["path"]
            for item in store.tree()
            if (
                item.get("type") == "blob"
                and item.get("path", "").startswith(prefix)
                and item.get("path", "").endswith(".json")
            )
        ]

        existing_records = [
            store.get(path)[0]
            for path in existing_paths
        ]

    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    duplicate = next(
        (
            record
            for record in existing_records
            if record.get("observation_date")
            == request.observation_date
        ),
        None,
    )

    if duplicate is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "A forward-test observation already exists for "
                f"{strategy_slug} v{version} on "
                f"{request.observation_date}."
            ),
        )

    if request.signals:
        signal_count = len(request.signals)
    else:
        signal_count = request.signal_count

    test_id = forward_test_id()
    created_at = now()
    fingerprint = strategy_fingerprint(strategy)
    snapshot = strategy_snapshot(strategy)

    record = {
        "schema_version": 2,
        "forward_test_id": test_id,
        "status": "RECORDED",
        "created_at": created_at,
        "strategy_slug": strategy_slug,
        "strategy_version": version,
        "strategy_name": strategy.get(
            "strategy_name"
        ),
        "strategy_fingerprint": fingerprint,
        "source_experiment_id": strategy.get(
            "source_experiment_id"
        ),
        "source_experiment_sha": strategy.get(
            "source_experiment_sha"
        ),
        "research_holdout_end": holdout_end,
        "observation_date": request.observation_date,
        "signal_count": signal_count,
        "signals": request.signals,
        "outcomes": request.outcomes,
        "market_context": request.market_context,
        "notes": request.notes,
        "metrics": request.metrics,
        "strategy_snapshot": snapshot,
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
        "strategy_slug": strategy_slug,
        "strategy_version": version,
        "forward_tests": records,
    }


@router.get(
    "/strategies/{strategy_slug}/v{version}/forward-tests/{test_id}",
)
def get_forward_test(
    strategy_slug: str,
    version: int,
    test_id: str,
) -> dict:
    path = forward_test_path(
        strategy_slug,
        version,
        test_id,
    )

    try:
        record, _ = store.get(path)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return record
