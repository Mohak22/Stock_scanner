# -*- coding: utf-8 -*-
"""
Created on Mon Sep  7 15:28:57 2026

@author: mohak
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any
from uuid import uuid4, UUID
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
    source_agent_run_id: str | None = None


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


def _is_github_not_found(exc: RuntimeError) -> bool:
    """Only a real GitHub HTTP 404 is treated as a missing file."""
    return "(404):" in str(exc)


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


def _stable_hash(document: dict) -> str:
    payload = json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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
        "lineage": record.get(
            "lineage",
            {},
        ),
        "snapshot": record.get(
            "snapshot",
            {},
        ),
        "reproducibility_hooks": (
            record
            .get("research_result", {})
            .get("research_config", {})
            .get("reproducibility_hooks", {})
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
        "survivorship_sensitivity": result.get(
            "survivorship_sensitivity", {}
        ),
        "random_baseline": result.get("random_baseline", {}),
    }


def experiment_summary(record: dict) -> dict:
    result = record.get("research_result", {})
    config = result.get("research_config", {})

    return {
        **experiment_metadata(record),
        "research_question": config.get(
            "research_question"
        ),
        "hypothesis": config.get(
            "hypothesis"
        ),
        "lineage": record.get(
            "lineage",
            {},
        ),
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
    result = record.get(
        "research_result",
        {}
    )

    config = result.get(
        "research_config",
        {}
    )

    return {
        **experiment_metadata(record),

        "research_question": config.get(
            "research_question"
        ),

        "hypothesis": config.get(
            "hypothesis"
        ),

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

        "lineage": record.get(
            "lineage",
            {},
        ),
    }


def _validate_research_result(
    research_result: dict,
) -> None:
    """
    Validate that a research result contains the complete
    canonical research contract required for experiment storage.

    Experiments are research snapshots.  A result without the
    canonical configuration or reproducibility metadata
    must not be persisted as an experiment.
    """

    if not isinstance(research_result, dict):
        raise HTTPException(
            status_code=400,
            detail="Research result must be an object.",
        )

    research_config = research_result.get(
        "research_config"
    )

    if not isinstance(research_config, dict):
        raise HTTPException(
            status_code=400,
            detail=(
                "Research result must contain "
                "research_config."
            ),
        )

    required_config_fields = {
        "research_schema_version",
        "development_start",
        "development_end",
        "signal_timing",
        "outcome_definition",
        "universe",
        "evaluation_horizons",
        "temporal_convention",
        "reproducibility_hooks",
    }

    missing_fields = (
        required_config_fields
        - set(research_config.keys())
    )

    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail=(
                "Research result is missing required "
                "configuration fields: "
                f"{sorted(missing_fields)}"
            ),
        )

    reproducibility_hooks = (
        research_config.get(
            "reproducibility_hooks"
        )
    )

    if not isinstance(
        reproducibility_hooks,
        dict,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Research result must contain "
                "reproducibility_hooks."
            ),
        )

    required_provenance_fields = {
        "data_revision",
        "universe_revision",
        "engine_version",
        "run_timestamp",
    }

    missing_provenance = (
        required_provenance_fields
        - set(reproducibility_hooks.keys())
    )

    if missing_provenance:
        raise HTTPException(
            status_code=400,
            detail=(
                "Research result is missing required "
                "reproducibility fields: "
                f"{sorted(missing_provenance)}"
            ),
        )

    if not research_result.get(
        "development"
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Research result must contain "
                "development results."
            ),
        )

def _validate_parent_experiment(
    parent_experiment_id: str | None,
) -> dict | None:
    if not parent_experiment_id:
        return None

    try:
        parent_record, _ = store.get_large(
            experiment_path(parent_experiment_id)
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "Parent experiment does not exist: "
                f"{parent_experiment_id}"
            ),
        ) from exc

    if parent_record.get("experiment_id") == parent_experiment_id:
        return parent_record

    raise HTTPException(
        status_code=400,
        detail=(
            "Parent experiment identity does not match "
            f"requested ID: {parent_experiment_id}"
        ),
    )


# ======================================================================
# EXPERIMENT PERSISTENCE
# ======================================================================

@router.post("/experiments", status_code=201)
def save_experiment(
    request: SaveExperimentRequest,
) -> dict:
    _validate_research_result(
        request.research_result
    )

    parent_experiment_id = (
        request.parent_experiment_id
        or request.research_result.get(
            "parent_experiment_id"
        )
    )

    parent_record = _validate_parent_experiment(
        parent_experiment_id
    )

    source_agent_run_id = request.source_agent_run_id
    
    if source_agent_run_id:
        try:
            stable_run_id = UUID(source_agent_run_id)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="Invalid source_agent_run_id.",
            ) from exc
    
        experiment_id_value = f"EXP-AI-{stable_run_id.hex.upper()}"
    
        # A previous attempt may already have saved this experiment.
        try:
            existing, existing_sha = store.get_large(experiment_path(experiment_id_value))
        except RuntimeError as exc:
            if not _is_github_not_found(exc):
                raise HTTPException(status_code=502, detail=f"Could not check AI experiment idempotency: {exc}") from exc
            existing = None
            existing_sha = None

        if existing is not None:
            if existing.get("source_agent_run_id") != source_agent_run_id:
                raise HTTPException(status_code=409, detail="Experiment identity collision.")
            metadata_path = experiment_metadata_path(experiment_id_value)
            try:
                metadata_sha = store.get_sha(metadata_path)
            except RuntimeError as exc:
                if not _is_github_not_found(exc):
                    raise HTTPException(status_code=502, detail=f"Could not inspect experiment metadata: {exc}") from exc
                metadata_sha = None
            try:
                store.put(metadata_path, experiment_metadata(existing),
                          f"Repair metadata for {experiment_id_value}", metadata_sha)
            except RuntimeError as exc:
                raise HTTPException(status_code=502, detail=f"Could not repair experiment metadata: {exc}") from exc
            return {
                "saved": True, "already_saved": True,
                "experiment_id": experiment_id_value,
                "status": existing.get("status", "SAVED"),
                "created_at": existing.get("created_at"),
                "parent_experiment_id": existing.get("parent_experiment_id"),
                "lineage": existing.get("lineage", {}),
                "commit_sha": existing_sha,
            }

    else:
        # Preserve existing manual Research Cockpit behaviour.
        experiment_id_value = experiment_id()
    
    created_at = now()

    lineage = {
        "parent_experiment_id": parent_experiment_id,
    }

    if parent_record is not None:
        lineage.update(
            {
                "parent_status": parent_record.get(
                    "status"
                ),
                "parent_created_at": parent_record.get(
                    "created_at"
                ),
                "parent_locked_at": parent_record.get(
                    "locked_at"
                ),
            }
        )

    record = {
        "schema_version": 2,
        "experiment_id": experiment_id_value,
        "source_agent_run_id": source_agent_run_id,
        "status": "SAVED",
        "name": request.name,
        "notes": request.notes,
        "tags": request.tags,
        "created_at": created_at,
        "updated_at": created_at,
        "locked_at": None,

        "parent_experiment_id": parent_experiment_id,

        "lineage": lineage,

        "snapshot": {
            "research_schema_version": (
                request.research_result
                .get("research_config", {})
                .get("research_schema_version")
            ),
            "research_question": (
                request.research_result
                .get("research_config", {})
                .get("research_question")
            ),
            "hypothesis": (
                request.research_result
                .get("research_config", {})
                .get("hypothesis")
            ),
            "reproducibility_hooks": (
                request.research_result
                .get("research_config", {})
                .get("reproducibility_hooks", {})
            ),
            "universe_membership_basis": (
                request.research_result
                .get("research_config", {})
                .get("universe_membership_basis")
            ),
            "temporal_convention": (
                request.research_result
                .get("research_config", {})
                .get("temporal_convention")
            ),
        },

        "research_result": request.research_result,
    }

    try:
        try:
            commit_sha = store.put(
                experiment_path(experiment_id_value), record,
                f"Save research experiment {experiment_id_value}",
            )
        except RuntimeError as exc:
            if not source_agent_run_id or not ("(409):" in str(exc) or "(422):" in str(exc)):
                raise
            existing, existing_sha = store.get_large(experiment_path(experiment_id_value))
            if existing.get("source_agent_run_id") != source_agent_run_id:
                raise HTTPException(status_code=409, detail="Experiment identity collision during concurrent save.") from exc
            record = existing
            commit_sha = existing_sha

        metadata_path = experiment_metadata_path(experiment_id_value)
        try:
            metadata_sha = store.get_sha(metadata_path)
        except RuntimeError as exc:
            if not _is_github_not_found(exc):
                raise
            metadata_sha = None
        store.put(metadata_path, experiment_metadata(record),
                  f"Save experiment metadata {experiment_id_value}", metadata_sha)
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "saved": True,
        "experiment_id": experiment_id_value,
        "status": "SAVED",
        "created_at": created_at,
        "parent_experiment_id": parent_experiment_id,
        "lineage": lineage,
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
            "message": (
                "Experiment is already locked and immutable."
            ),
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
        experiment, experiment_sha = store.get_large(
            experiment_path(request.experiment_id)
        )
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
    research_result = experiment.get("research_result")
    config = research_result.get("research_config") if isinstance(research_result, dict) else None

    if not isinstance(config, dict):
        raise HTTPException(
            status_code=409,
            detail="Locked experiment does not contain a valid research configuration.",
        )

    source_snapshot = experiment.get("snapshot", {})
    if not isinstance(source_snapshot, dict) or not source_snapshot:
        source_snapshot = {
            "research_schema_version": config.get("research_schema_version"),
            "research_question": config.get("research_question"),
            "hypothesis": config.get("hypothesis"),
            "reproducibility_hooks": config.get(
                "reproducibility_hooks", {}
            ),
            "universe_membership_basis": config.get(
                "universe_membership_basis"
            ),
            "temporal_convention": config.get(
                "temporal_convention"
            ),
        }

    strategy_snapshot = {
        "source_experiment_id": request.experiment_id,
        "source_experiment_sha": experiment_sha,
        "source_experiment_locked_at": experiment.get("locked_at"),
        "research_schema_version": config.get(
            "research_schema_version"
        ),
        "research_question": config.get("research_question"),
        "hypothesis": config.get("hypothesis"),
        "research_config": config,
        "evaluation_evidence": {
            "development": research_result.get("development"),
            "validation": research_result.get("validation"),
            "final_holdout": research_result.get("final_holdout"),
        },
        "experiment_snapshot": source_snapshot,
    }

    strategy_fingerprint = _stable_hash(strategy_snapshot)
    created_at = now()

    record = {
        "schema_version": 3,
        "strategy_name": request.strategy_name.strip(),
        "strategy_slug": slug,
        "version": version,
        "status": "DRAFT",
        "created_at": created_at,
        "updated_at": created_at,
        "locked_at": None,
        "source_experiment_id": request.experiment_id,
        "source_experiment_sha": experiment_sha,
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
        "evaluation_evidence": strategy_snapshot[
            "evaluation_evidence"
        ],
        "snapshot": strategy_snapshot,
        "strategy_fingerprint": strategy_fingerprint,
        "lineage": {
            "source_experiment_id": request.experiment_id,
            "source_experiment_parent_id": experiment.get(
                "parent_experiment_id"
            ),
            "source_experiment_lineage": experiment.get(
                "lineage",
                {},
            ),
            "source_experiment_reproducibility": config.get(
                "reproducibility_hooks",
                {},
            ),
            "source_experiment_sha": experiment_sha,
            "strategy_fingerprint": strategy_fingerprint,
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
        return {
            **record,
            "message": "Strategy version is already locked and immutable.",
        }

    source_experiment_id = record.get("source_experiment_id")
    if not source_experiment_id:
        raise HTTPException(
            status_code=409,
            detail="Strategy is missing its source experiment.",
        )

    try:
        source_experiment, _ = store.get_large(
            experiment_path(source_experiment_id)
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=409,
            detail=(
                "Source experiment is no longer available: "
                f"{source_experiment_id}"
            ),
        ) from exc

    if source_experiment.get("status") != "LOCKED":
        raise HTTPException(
            status_code=409,
            detail="Source experiment must remain LOCKED before strategy locking.",
        )

    if not record.get("snapshot") or not record.get("strategy_fingerprint"):
        raise HTTPException(
            status_code=409,
            detail="Strategy snapshot and fingerprint are required before locking.",
        )

    locked_at = now()
    record["status"] = "LOCKED"
    record["locked_at"] = locked_at
    record["updated_at"] = locked_at

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


@router.delete("/strategies/{strategy_slug}/v{version}")
def delete_strategy(
    strategy_slug: str,
    version: int,
) -> dict:
    path = strategy_path(strategy_slug, version)

    try:
        record, sha = store.get(path)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    if record.get("status") == "LOCKED":
        raise HTTPException(
            status_code=409,
            detail=(
                "Locked strategy versions are immutable and cannot be deleted. "
                "Create a new strategy version instead."
            ),
        )

    try:
        commit_sha = store.delete(
            path,
            sha,
            (
                f"Delete strategy "
                f"{record.get('strategy_name', strategy_slug)} v{version}"
            ),
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    return {
        "deleted": True,
        "strategy_slug": strategy_slug,
        "version": version,
        "commit_sha": commit_sha,
    }
