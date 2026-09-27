# -*- coding: utf-8 -*-
"""
Created on Mon Sep  7 15:28:57 2026

@author: mohak
"""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


OWNER = "Mohak22"
REPO = "STOCK_SCANNER_DATA"
BRANCH = "main"
API = "https://api.github.com"

EXP_PREFIX = "research/experiments/"
STRAT_PREFIX = "research/strategies/"


router = APIRouter(
    prefix="/research",
    tags=["experiments"],
)


# ======================================================================
# REQUEST MODELS
# ======================================================================

class SaveExperimentRequest(BaseModel):
    research_result: dict[str, Any]
    name: str | None = None
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    parent_experiment_id: str | None = None


class CompareExperimentsRequest(BaseModel):
    experiment_ids: list[str] = Field(
        min_length=2,
        max_length=5,
    )


class CreateStrategyRequest(BaseModel):
    experiment_id: str
    strategy_name: str
    description: str | None = None
    version_notes: str | None = None


# ======================================================================
# GITHUB STORAGE
# ======================================================================

class GitHubStore:

    def __init__(self) -> None:

        self.repository = (
            f"{OWNER}/{REPO}"
        )

        self.token = os.getenv(
            "STOCK_SCANNER_DATA_TOKEN"
        )

    def _request(
        self,
        method: str,
        url: str,
        body: dict | None = None,
    ) -> dict:

        if not self.token:

            raise RuntimeError(
                "STOCK_SCANNER_DATA_TOKEN "
                "is not configured."
            )

        headers = {
            "Accept": (
                "application/vnd.github+json"
            ),
            "Authorization": (
                f"Bearer {self.token}"
            ),
            "User-Agent": (
                "Stock-Scanner-Research-Cockpit"
            ),
            "X-GitHub-Api-Version": (
                "2022-11-28"
            ),
        }

        data = None

        if body is not None:

            data = json.dumps(
                body,
                ensure_ascii=False,
            ).encode("utf-8")

            headers["Content-Type"] = (
                "application/json"
            )

        request = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method=method,
        )

        try:

            with urllib.request.urlopen(
                request,
                timeout=60,
            ) as response:

                raw = (
                    response
                    .read()
                    .decode("utf-8")
                )

                return (
                    json.loads(raw)
                    if raw
                    else {}
                )

        except urllib.error.HTTPError as exc:

            message = (
                exc
                .read()
                .decode(
                    "utf-8",
                    errors="replace",
                )
            )

            try:

                message = json.loads(
                    message
                ).get(
                    "message",
                    message,
                )

            except json.JSONDecodeError:

                pass

            raise RuntimeError(
                f"GitHub request failed "
                f"({exc.code}): {message}"
            ) from exc

        except urllib.error.URLError as exc:

            raise RuntimeError(
                "Could not reach GitHub: "
                f"{exc.reason}"
            ) from exc

    def url(
        self,
        path: str,
    ) -> str:

        return (
            f"{API}/repos/"
            f"{self.repository}/contents/"
            f"{path}?ref={BRANCH}"
        )

    def get(
        self,
        path: str,
    ) -> tuple[dict, str]:
    
        payload = self._request(
            "GET",
            self.url(path),
        )
    
        if (
            "content" not in payload
            or "sha" not in payload
        ):
            raise RuntimeError(
                f"GitHub file content missing: {path}"
            )
    
        content = base64.b64decode(
            payload["content"]
        ).decode("utf-8")
    
        return (
            json.loads(content),
            payload["sha"],
        )
    
    def get_sha(
        self,
        path: str,
    ) -> str:
    
        payload = self._request(
            "GET",
            self.url(path),
        )
    
        if "sha" not in payload:
            raise RuntimeError(
                f"GitHub file SHA missing: {path}"
            )
    
        return payload["sha"]

    def get_large(
        self,
        path: str,
    ) -> tuple[dict, str]:
    
        payload = self._request(
            "GET",
            self.url(path),
        )
    
        if "sha" not in payload:
            raise RuntimeError(
                f"GitHub file SHA missing: {path}"
            )
    
        blob_sha = payload["sha"]
    
        record = self.get_blob(blob_sha)
    
        return record, blob_sha

    def put(
        self,
        path: str,
        document: dict,
        message: str,
        sha: str | None = None,
    ) -> str:
    
        if not isinstance(document, dict) or not document:
            raise RuntimeError(
                f"Cannot save empty document: {path}"
            )
    
        try:
            serialized = json.dumps(
                document,
                indent=2,
                ensure_ascii=False,
            )
        except (TypeError, ValueError) as exc:
            raise RuntimeError(
                f"Could not serialize document: {path}"
            ) from exc
    
        if not serialized.strip():
            raise RuntimeError(
                f"Serialized document is empty: {path}"
            )
    
        encoded = base64.b64encode(
            serialized.encode("utf-8")
        ).decode("ascii")
    
        body = {
            "message": message,
            "content": encoded,
            "branch": BRANCH,
        }
    
        if sha:
            body["sha"] = sha
    
        payload = self._request(
            "PUT",
            self.url(path),
            body,
        )
    
        commit_sha = payload.get("commit", {}).get("sha", "")
    
        if not commit_sha:
            raise RuntimeError(
                f"GitHub did not return a commit SHA for: {path}"
            )
    
        return commit_sha    
    
    def delete(
        self,
        path: str,
        sha: str,
        message: str,
    ) -> str:

        body = {
            "message": message,
            "sha": sha,
            "branch": BRANCH,
        }

        payload = self._request(
            "DELETE",
            self.url(path),
            body,
        )

        return (
            payload
            .get("commit", {})
            .get("sha", "")
        )
    
    def get_blob(self, sha: str) -> dict:
        payload = self._request(
            "GET",
            f"{API}/repos/{self.repository}/git/blobs/{sha}",
        )
    
        if "content" not in payload:
            raise RuntimeError(
                f"GitHub blob content missing: {sha}"
            )
    
        content = base64.b64decode(
            payload["content"]
        ).decode("utf-8")
    
        return json.loads(content)

    def tree(self) -> list[dict]:

        payload = self._request(
            "GET",
            (
                f"{API}/repos/"
                f"{self.repository}/git/trees/"
                f"{BRANCH}?recursive=1"
            ),
        )

        return payload.get(
            "tree",
            [],
        )


store = GitHubStore()


# ======================================================================
# HELPERS
# ======================================================================

def now() -> str:
    return datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).isoformat()


def experiment_id() -> str:
    current = datetime.now(
        ZoneInfo("Asia/Kolkata")
    )
    suffix = uuid4().hex[:4].upper()
    return f"EXP-{current:%Y%m%d-%H%M%S}-{suffix}"


def experiment_path(experiment_id: str) -> str:
    return f"{EXP_PREFIX}{experiment_id}.json"


def experiment_metadata_path(experiment_id: str) -> str:
    return f"{EXP_PREFIX}{experiment_id}.meta.json"


def strategy_slug(name: str) -> str:
    slug = re.sub(
        r"[^A-Za-z0-9]+",
        "-",
        name.strip(),
    ).strip("-").lower()

    if not slug:
        raise HTTPException(
            status_code=400,
            detail="Invalid strategy name.",
        )

    return slug


def strategy_path(slug: str, version: int) -> str:
    return f"{STRAT_PREFIX}{slug}/v{version}.json"


def experiment_metadata(record: dict) -> dict:
    return {
        "schema_version": record.get("schema_version", 2),
        "experiment_id": record["experiment_id"],
        "name": record.get("name"),
        "status": record.get("status"),
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
        "locked_at": record.get("locked_at"),
        "parent_experiment_id": record.get(
            "parent_experiment_id"
        ),
        "tags": record.get("tags", []),
    }


def _stage_result(result: dict | None) -> dict | None:
    if not isinstance(result, dict):
        return None

    return {
        "summary": result.get("summary", {}),
        "performance": result.get("performance", {}),
        "diagnostics": result.get("diagnostics", {}),
        "analysis": result.get("analysis", {}),
        "warnings": result.get("warnings", []),
    }


def experiment_summary(record: dict) -> dict:
    result = record.get("research_result", {})
    config = result.get("research_config", {})

    return {
        **experiment_metadata(record),
        "research_question": config.get("research_question"),
        "hypothesis": config.get("hypothesis"),
        "research_config": config,
        "development": _stage_result(
            result.get("development")
        ),
        "validation": _stage_result(
            result.get("validation")
        ),
        "final_holdout": _stage_result(
            result.get("final_holdout")
        ),
    }


def experiment_compare_summary(record: dict) -> dict:
    result = record.get("research_result", {})
    config = result.get("research_config", {})

    return {
        **experiment_metadata(record),
        "research_question": config.get("research_question"),
        "hypothesis": config.get("hypothesis"),
        "research_config": config,
        "development": _stage_result(
            result.get("development")
        ),
        "validation": _stage_result(
            result.get("validation")
        ),
        "final_holdout": _stage_result(
            result.get("final_holdout")
        ),
        "lineage": {
            "parent_experiment_id": record.get(
                "parent_experiment_id"
            ),
        },
    }


def _validate_research_result(
    research_result: dict,
) -> None:
    config = research_result.get(
        "research_config"
    )

    if not isinstance(config, dict):
        raise HTTPException(
            status_code=400,
            detail="research_result.research_config is required.",
        )

    required = [
        "research_question",
        "hypothesis",
        "development_start",
        "development_end",
        "universe",
        "features",
        "entry_conditions",
        "evaluation_horizons",
    ]

    missing = [
        key for key in required
        if config.get(key) in (None, "")
    ]

    if missing:
        raise HTTPException(
            status_code=400,
            detail=(
                "Research result is missing canonical fields: "
                + ", ".join(missing)
            ),
        )

    if research_result.get("development") is None:
        raise HTTPException(
            status_code=400,
            detail="Development evaluation result is required.",
        )


# ======================================================================
# EXPERIMENT PERSISTENCE
# ======================================================================

@router.post("/experiments", status_code=201)
def save_experiment(request: SaveExperimentRequest) -> dict:
    _validate_research_result(
        request.research_result
    )

    experiment_id_value = experiment_id()
    created_at = now()

    record = {
        "schema_version": 2,
        "experiment_id": experiment_id_value,
        "status": "SAVED",
        "name": request.name,
        "notes": request.notes,
        "tags": request.tags,
        "created_at": created_at,
        "updated_at": created_at,
        "locked_at": None,
        "parent_experiment_id": request.parent_experiment_id
        or request.research_result.get("parent_experiment_id"),
        "research_result": request.research_result,
    }

    try:
        commit_sha = store.put(
            experiment_path(experiment_id_value),
            record,
            f"Save research experiment {experiment_id_value}",
        )

        store.put(
            experiment_metadata_path(experiment_id_value),
            experiment_metadata(record),
            f"Save experiment metadata {experiment_id_value}",
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    return {
        "saved": True,
        "experiment_id": experiment_id_value,
        "status": "SAVED",
        "created_at": created_at,
        "commit_sha": commit_sha,
    }


@router.get("/experiments")
def list_experiments() -> dict:
    try:
        paths = [
            item["path"]
            for item in store.tree()
            if (
                item.get("type") == "blob"
                and item.get("path", "").startswith(EXP_PREFIX)
                and item.get("path", "").endswith(".meta.json")
            )
        ]

        records = [
            experiment_summary(store.get(path)[0])
            for path in paths
        ]

    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    records.sort(
        key=lambda item: item.get("created_at") or "",
        reverse=True,
    )

    return {
        "count": len(records),
        "experiments": records,
    }


@router.get("/experiments/{experiment_id}")
def get_experiment(experiment_id: str) -> dict:
    try:
        record, _ = store.get_large(
            experiment_path(experiment_id)
        )
        return record
    except RuntimeError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.delete("/experiments/{experiment_id}")
def delete_experiment(experiment_id: str) -> dict:
    path = experiment_path(experiment_id)

    try:
        record, sha = store.get_large(path)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    if record.get("status") == "LOCKED":
        raise HTTPException(
            status_code=409,
            detail=(
                "Locked experiments are immutable and cannot be deleted. "
                "Create a new experiment with lineage instead."
            ),
        )

    try:
        commit_sha = store.delete(
            path,
            sha,
            f"Delete research experiment {experiment_id}",
        )

        metadata_path = experiment_metadata_path(
            experiment_id
        )

        try:
            metadata_sha = store.get_sha(
                metadata_path
            )
            store.delete(
                metadata_path,
                metadata_sha,
                f"Delete experiment metadata {experiment_id}",
            )
        except RuntimeError:
            pass

    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    return {
        "deleted": True,
        "experiment_id": experiment_id,
        "commit_sha": commit_sha,
    }


@router.post("/experiments/compare")
def compare_experiments(
    request: CompareExperimentsRequest,
) -> dict:
    records = []

    for experiment_id_value in request.experiment_ids:
        try:
            record, _ = store.get_large(
                experiment_path(experiment_id_value)
            )
        except RuntimeError as exc:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Could not load experiment "
                    f"{experiment_id_value}: {exc}"
                ),
            ) from exc

        records.append(
            experiment_compare_summary(record)
        )

    return {
        "experiment_ids": request.experiment_ids,
        "experiments": records,
    }


@router.post("/experiments/{experiment_id}/lock")
def lock_experiment(experiment_id: str) -> dict:
    path = experiment_path(experiment_id)
    metadata_path = experiment_metadata_path(
        experiment_id
    )

    try:
        record, sha = store.get_large(path)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    if record.get("status") == "LOCKED":
        return {
            "locked": True,
            "experiment_id": experiment_id,
            "status": "LOCKED",
            "locked_at": record.get("locked_at"),
        }

    holdout = (
        record.get("research_result", {})
        .get("final_holdout")
    )

    if holdout is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Final holdout evaluation must be present "
                "before an experiment can be locked."
            ),
        )

    locked_at = now()
    record["status"] = "LOCKED"
    record["locked_at"] = locked_at
    record["updated_at"] = locked_at

    try:
        commit_sha = store.put(
            path,
            record,
            f"Lock research experiment {experiment_id}",
            sha,
        )

        metadata_sha = store.get_sha(
            metadata_path
        )

        store.put(
            metadata_path,
            experiment_metadata(record),
            f"Update locked experiment metadata {experiment_id}",
            metadata_sha,
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Could not lock experiment: {exc}",
        ) from exc

    return {
        "locked": True,
        "experiment_id": experiment_id,
        "status": "LOCKED",
        "locked_at": locked_at,
        "commit_sha": commit_sha,
    }


# ======================================================================
# STRATEGY VERSIONING
# ======================================================================

@router.post("/strategies", status_code=201)
def create_strategy_version(
    request: CreateStrategyRequest,
) -> dict:
    try:
        experiment = store.get_large(
            experiment_path(request.experiment_id)
        )[0]
        tree = store.tree()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    if experiment.get("status") != "LOCKED":
        raise HTTPException(
            status_code=409,
            detail=(
                "Only a LOCKED experiment can create a strategy version."
            ),
        )

    slug = strategy_slug(request.strategy_name)

    prefix = f"{STRAT_PREFIX}{slug}/v"
    versions = []

    for item in tree:
        path = item.get("path", "")
        if path.startswith(prefix) and path.endswith(".json"):
            value = path[len(prefix):-5]
            if value.isdigit():
                versions.append(int(value))

    version = max(versions, default=0) + 1
    research_result = experiment["research_result"]
    config = research_result["research_config"]

    record = {
        "schema_version": 2,
        "strategy_name": request.strategy_name.strip(),
        "strategy_slug": slug,
        "version": version,
        "status": "DRAFT",
        "created_at": now(),
        "locked_at": None,
        "source_experiment_id": request.experiment_id,
        "source_experiment_locked_at": experiment.get(
            "locked_at"
        ),
        "parent_strategy_version": None,
        "description": request.description,
        "version_notes": request.version_notes,
        "research_question": config.get(
            "research_question"
        ),
        "hypothesis": config.get("hypothesis"),
        "research_config": config,
        "evaluation_evidence": {
            "development": research_result.get(
                "development"
            ),
            "validation": research_result.get(
                "validation"
            ),
            "final_holdout": research_result.get(
                "final_holdout"
            ),
        },
        "lineage": {
            "source_experiment_id": request.experiment_id,
            "source_experiment_parent_id": experiment.get(
                "parent_experiment_id"
            ),
        },
    }

    try:
        commit_sha = store.put(
            strategy_path(slug, version),
            record,
            (
                f"Create strategy "
                f"{request.strategy_name} v{version}"
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


@router.get("/strategies")
def list_strategies() -> dict:
    try:
        paths = [
            item["path"]
            for item in store.tree()
            if (
                item.get("type") == "blob"
                and item.get("path", "").startswith(STRAT_PREFIX)
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
            item.get("strategy_name", ""),
            item.get("version", 0),
        )
    )

    return {
        "count": len(records),
        "strategies": records,
    }


@router.get("/strategies/{strategy_slug}/v{version}")
def get_strategy(
    strategy_slug: str,
    version: int,
) -> dict:
    try:
        record, _ = store.get(
            strategy_path(strategy_slug, version)
        )
        return record
    except RuntimeError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.post("/strategies/{strategy_slug}/v{version}/lock")
def lock_strategy(
    strategy_slug: str,
    version: int,
) -> dict:
    path = strategy_path(
        strategy_slug,
        version,
    )

    try:
        record, sha = store.get(path)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    if record.get("status") == "LOCKED":
        return record

    if not record.get("source_experiment_id"):
        raise HTTPException(
            status_code=409,
            detail="Strategy is missing its source experiment.",
        )

    record["status"] = "LOCKED"
    record["locked_at"] = now()

    try:
        commit_sha = store.put(
            path,
            record,
            (
                f"Lock strategy "
                f"{record['strategy_name']} v{version}"
            ),
            sha,
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
