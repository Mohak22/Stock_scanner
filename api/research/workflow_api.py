# -*- coding: utf-8 -*-
"""
Created on Mon Sep  7 18:09:36 2026

@author: mohak
"""

# -*- coding: utf-8 -*-

import copy
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.research.experiment_api import (
    store,
    experiment_path,
    strategy_path,
)


router = APIRouter(
    prefix="/research",
    tags=["research-workflow"],
)


# ======================================================================
# CONSTANTS
# ======================================================================

TRAINING = "TRAINING"
VALIDATION = "VALIDATION"
TESTING = "TESTING"
FINAL_ASSESSMENT = "FINAL_ASSESSMENT"
RESEARCH_READY = "RESEARCH_READY"

ALLOWED_STAGES = {
    TRAINING,
    VALIDATION,
    TESTING,
    FINAL_ASSESSMENT,
    RESEARCH_READY,
}


# ======================================================================
# REQUEST MODELS
# ======================================================================

class StartTrainingRequest(BaseModel):
    experiment_id: str


class PromoteRequest(BaseModel):
    notes: str | None = None


class ExecuteStrategyRequest(BaseModel):
    notes: str | None = None


class FinalAssessmentRequest(BaseModel):
    decision: str = Field(
        pattern="^(RESEARCH_READY|REJECTED|NEEDS_RESEARCH)$"
    )
    notes: str | None = None


class SaveResearchReadyRequest(BaseModel):
    strategy_name: str | None = None
    description: str | None = None
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)


# ======================================================================
# HELPERS
# ======================================================================

def now() -> str:
    return datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).isoformat()


def load_experiment(experiment_id: str) -> tuple[dict, str]:
    try:
        return store.get(
            experiment_path(experiment_id)
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


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


def save_document(
    path: str,
    document: dict,
    message: str,
    sha: str | None = None,
) -> str:
    try:
        return store.put(
            path,
            document,
            message,
            sha,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc


def ensure_stage(
    strategy: dict,
    expected: str,
) -> None:
    current = strategy.get(
        "workflow_stage",
        TRAINING,
    )

    if current != expected:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Strategy is currently in "
                f"'{current}' stage. "
                f"Expected '{expected}'."
            ),
        )


def get_research_result(
    strategy: dict,
) -> dict:
    result = strategy.get(
        "research_result"
    )

    if isinstance(result, dict):
        return result

    source_experiment_id = strategy.get(
        "source_experiment_id"
    )

    if not source_experiment_id:
        raise HTTPException(
            status_code=409,
            detail=(
                "Strategy does not contain "
                "a research result or source "
                "experiment."
            ),
        )

    experiment, _ = load_experiment(
        source_experiment_id
    )

    result = experiment.get(
        "research_result",
        {},
    )

    if not isinstance(result, dict):
        raise HTTPException(
            status_code=409,
            detail="Source experiment has no valid research result.",
        )

    return result


def stage_snapshot(
    strategy: dict,
) -> dict:
    return {
        "workflow_stage": strategy.get(
            "workflow_stage",
            TRAINING,
        ),
        "training": strategy.get(
            "training"
        ),
        "validation": strategy.get(
            "validation"
        ),
        "testing": strategy.get(
            "testing"
        ),
        "final_assessment": strategy.get(
            "final_assessment"
        ),
    }


# ======================================================================
# C10 — TRAINING STATE
# ======================================================================

@router.post(
    "/workflow/strategies/{strategy_slug}/v{version}/training",
)
def start_training(
    strategy_slug: str,
    version: int,
    request: StartTrainingRequest,
) -> dict:

    strategy, sha = load_strategy(
        strategy_slug,
        version,
    )

    if strategy.get(
        "status"
    ) == "LOCKED":
        raise HTTPException(
            status_code=409,
            detail=(
                "A locked strategy cannot "
                "be moved back into training."
            ),
        )

    source_experiment_id = strategy.get(
        "source_experiment_id"
    )

    if (
        source_experiment_id
        != request.experiment_id
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "The supplied experiment does not "
                "match the strategy's source experiment."
            ),
        )

    current_stage = strategy.get(
        "workflow_stage"
    )

    if current_stage not in (
        None,
        TRAINING,
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Training can only be started "
                "before validation."
            ),
        )

    strategy["workflow_stage"] = TRAINING
    strategy["workflow_started_at"] = (
        strategy.get(
            "workflow_started_at"
        )
        or now()
    )
    strategy["training_state"] = "ACTIVE"

    commit_sha = save_document(
        strategy_path(
            strategy_slug,
            version,
        ),
        strategy,
        (
            f"Start training workflow "
            f"{strategy['strategy_name']} "
            f"v{version}"
        ),
        sha,
    )

    return {
        "workflow_started": True,
        "strategy_slug": strategy_slug,
        "version": version,
        "stage": TRAINING,
        "training_state": "ACTIVE",
        "commit_sha": commit_sha,
    }


# ======================================================================
# C11 — TRAINING → VALIDATION
# ======================================================================

@router.post(
    "/workflow/strategies/{strategy_slug}/v{version}/promote-to-validation",
)
def promote_to_validation(
    strategy_slug: str,
    version: int,
    request: PromoteRequest,
) -> dict:

    strategy, sha = load_strategy(
        strategy_slug,
        version,
    )

    ensure_stage(
        strategy,
        TRAINING,
    )

    if strategy.get(
        "status"
    ) == "LOCKED":
        raise HTTPException(
            status_code=409,
            detail="Strategy is already locked.",
        )

    research_result = get_research_result(
        strategy
    )

    training = research_result.get(
        "training"
    )

    if not training:
        raise HTTPException(
            status_code=409,
            detail=(
                "Training result is missing. "
                "Run research before promoting "
                "to validation."
            ),
        )

    strategy["workflow_stage"] = VALIDATION
    strategy["validation_state"] = "LOCKED"
    strategy["training_state"] = "COMPLETE"
    strategy["validation_started_at"] = now()
    strategy["validation_notes"] = request.notes

    # Freeze the exact configuration used.
    strategy["locked_research_config"] = copy.deepcopy(
        strategy.get(
            "research_config",
            {},
        )
    )

    commit_sha = save_document(
        strategy_path(
            strategy_slug,
            version,
        ),
        strategy,
        (
            f"Promote strategy "
            f"{strategy['strategy_name']} "
            f"v{version} to validation"
        ),
        sha,
    )

    return {
        "promoted": True,
        "strategy_slug": strategy_slug,
        "version": version,
        "stage": VALIDATION,
        "training_state": "COMPLETE",
        "validation_state": "LOCKED",
        "locked_research_config": strategy[
            "locked_research_config"
        ],
        "commit_sha": commit_sha,
    }


# ======================================================================
# C12 — VALIDATION → TESTING
# ======================================================================

@router.post(
    "/workflow/strategies/{strategy_slug}/v{version}/promote-to-testing",
)
def promote_to_testing(
    strategy_slug: str,
    version: int,
    request: PromoteRequest,
) -> dict:

    strategy, sha = load_strategy(
        strategy_slug,
        version,
    )

    ensure_stage(
        strategy,
        VALIDATION,
    )

    if strategy.get(
        "validation_state"
    ) != "LOCKED":
        raise HTTPException(
            status_code=409,
            detail=(
                "Validation must be locked "
                "before testing."
            ),
        )

    research_result = get_research_result(
        strategy
    )

    validation = research_result.get(
        "validation"
    )

    if not validation:
        raise HTTPException(
            status_code=409,
            detail=(
                "Validation result is missing. "
                "A strategy cannot proceed to "
                "testing without validation."
            ),
        )

    strategy["workflow_stage"] = TESTING
    strategy["validation_state"] = "COMPLETE"
    strategy["testing_state"] = "LOCKED"
    strategy["testing_started_at"] = now()
    strategy["testing_notes"] = request.notes

    # Testing must use exactly what was frozen
    # when entering validation.
    strategy["testing_research_config"] = copy.deepcopy(
        strategy.get(
            "locked_research_config",
            strategy.get(
                "research_config",
                {},
            ),
        )
    )

    commit_sha = save_document(
        strategy_path(
            strategy_slug,
            version,
        ),
        strategy,
        (
            f"Promote strategy "
            f"{strategy['strategy_name']} "
            f"v{version} to testing"
        ),
        sha,
    )

    return {
        "promoted": True,
        "strategy_slug": strategy_slug,
        "version": version,
        "stage": TESTING,
        "validation_state": "COMPLETE",
        "testing_state": "LOCKED",
        "testing_research_config": strategy[
            "testing_research_config"
        ],
        "commit_sha": commit_sha,
    }


# ======================================================================
# C13 — LOCKED STRATEGY EXECUTION
# ======================================================================

@router.post(
    "/workflow/strategies/{strategy_slug}/v{version}/execute",
)
def execute_locked_strategy(
    strategy_slug: str,
    version: int,
    request: ExecuteStrategyRequest,
) -> dict:

    strategy, sha = load_strategy(
        strategy_slug,
        version,
    )

    if strategy.get(
        "workflow_stage"
    ) != TESTING:
        raise HTTPException(
            status_code=409,
            detail=(
                "Locked strategy execution is "
                "only available after the strategy "
                "has entered testing."
            ),
        )

    if strategy.get(
        "testing_state"
    ) != "LOCKED":
        raise HTTPException(
            status_code=409,
            detail=(
                "Testing configuration is not locked."
            ),
        )

    if strategy.get(
        "status"
    ) != "LOCKED":
        raise HTTPException(
            status_code=409,
            detail=(
                "The strategy itself must be "
                "LOCKED before execution."
            ),
        )

    research_result = get_research_result(
        strategy
    )

    testing = research_result.get(
        "testing"
    )

    if not testing:
        raise HTTPException(
            status_code=409,
            detail=(
                "Testing result is missing."
            ),
        )

    strategy["execution_state"] = "EXECUTED"
    strategy["executed_at"] = now()
    strategy["execution_notes"] = request.notes

    # Preserve the exact testing result used
    # for final assessment.
    strategy["executed_testing_result"] = copy.deepcopy(
        testing
    )

    commit_sha = save_document(
        strategy_path(
            strategy_slug,
            version,
        ),
        strategy,
        (
            f"Execute locked strategy "
            f"{strategy['strategy_name']} "
            f"v{version}"
        ),
        sha,
    )

    return {
        "executed": True,
        "strategy_slug": strategy_slug,
        "version": version,
        "stage": TESTING,
        "execution_state": "EXECUTED",
        "testing_result": testing,
        "commit_sha": commit_sha,
    }


# ======================================================================
# C14 — FINAL ASSESSMENT
# ======================================================================

@router.post(
    "/workflow/strategies/{strategy_slug}/v{version}/final-assessment",
)
def final_assessment(
    strategy_slug: str,
    version: int,
    request: FinalAssessmentRequest,
) -> dict:

    strategy, sha = load_strategy(
        strategy_slug,
        version,
    )

    if strategy.get(
        "workflow_stage"
    ) != TESTING:
        raise HTTPException(
            status_code=409,
            detail=(
                "Final assessment is available "
                "only after testing."
            ),
        )

    if strategy.get(
        "execution_state"
    ) != "EXECUTED":
        raise HTTPException(
            status_code=409,
            detail=(
                "Execute the locked strategy "
                "before final assessment."
            ),
        )

    research_result = get_research_result(
        strategy
    )

    training = research_result.get(
        "training",
        {},
    )
    validation = research_result.get(
        "validation",
        {},
    )
    testing = research_result.get(
        "testing",
        {},
    )

    diagnostics = {}

    for stage_name, stage_data in (
        ("training", training),
        ("validation", validation),
        ("testing", testing),
    ):
        if isinstance(stage_data, dict):
            diagnostics[stage_name] = stage_data.get(
                "diagnostics",
                {},
            )

    assessment = {
        "decision": request.decision,
        "assessed_at": now(),
        "notes": request.notes,
        "training": training,
        "validation": validation,
        "testing": testing,
        "diagnostics": diagnostics,
    }

    strategy["final_assessment"] = assessment
    strategy["workflow_stage"] = FINAL_ASSESSMENT
    strategy["assessment_state"] = "COMPLETE"

    commit_sha = save_document(
        strategy_path(
            strategy_slug,
            version,
        ),
        strategy,
        (
            f"Final assessment for "
            f"{strategy['strategy_name']} "
            f"v{version}"
        ),
        sha,
    )

    return {
        "assessed": True,
        "strategy_slug": strategy_slug,
        "version": version,
        "stage": FINAL_ASSESSMENT,
        "assessment": assessment,
        "commit_sha": commit_sha,
    }


# ======================================================================
# C15 — SAVE / EXPORT RESEARCH-READY STRATEGY
# ======================================================================

@router.post(
    "/workflow/strategies/{strategy_slug}/v{version}/save-research-ready",
    status_code=201,
)
def save_research_ready_strategy(
    strategy_slug: str,
    version: int,
    request: SaveResearchReadyRequest,
) -> dict:

    strategy, sha = load_strategy(
        strategy_slug,
        version,
    )

    if strategy.get(
        "workflow_stage"
    ) != FINAL_ASSESSMENT:
        raise HTTPException(
            status_code=409,
            detail=(
                "Final assessment must be completed "
                "before saving a research-ready strategy."
            ),
        )

    assessment = strategy.get(
        "final_assessment",
        {},
    )

    if assessment.get(
        "decision"
    ) != RESEARCH_READY:
        raise HTTPException(
            status_code=409,
            detail=(
                "Final assessment must have "
                "decision='RESEARCH_READY'."
            ),
        )

    if strategy.get(
        "status"
    ) != "LOCKED":
        raise HTTPException(
            status_code=409,
            detail=(
                "Strategy must be LOCKED before "
                "being exported as research-ready."
            ),
        )

    strategy["workflow_stage"] = RESEARCH_READY
    strategy["research_ready"] = True
    strategy["research_ready_at"] = now()

    if request.strategy_name:
        strategy["research_ready_name"] = (
            request.strategy_name.strip()
        )

    if request.description:
        strategy["research_ready_description"] = (
            request.description
        )

    strategy["research_ready_notes"] = request.notes
    strategy["research_ready_tags"] = request.tags

    # Explicit research-ready package.
    strategy["research_ready_package"] = {
        "strategy_name": (
            request.strategy_name
            or strategy.get("strategy_name")
        ),
        "strategy_slug": strategy.get(
            "strategy_slug"
        ),
        "version": strategy.get(
            "version"
        ),
        "source_experiment_id": strategy.get(
            "source_experiment_id"
        ),
        "research_config": copy.deepcopy(
            strategy.get(
                "testing_research_config",
                strategy.get(
                    "locked_research_config",
                    strategy.get(
                        "research_config",
                        {},
                    ),
                ),
            )
        ),
        "final_assessment": copy.deepcopy(
            assessment
        ),
        "created_at": strategy.get(
            "created_at"
        ),
        "research_ready_at": strategy[
            "research_ready_at"
        ],
    }

    commit_sha = save_document(
        strategy_path(
            strategy_slug,
            version,
        ),
        strategy,
        (
            f"Save research-ready strategy "
            f"{strategy['strategy_name']} "
            f"v{version}"
        ),
        sha,
    )

    return {
        "saved": True,
        "research_ready": True,
        "strategy_slug": strategy_slug,
        "version": version,
        "stage": RESEARCH_READY,
        "research_ready_package": strategy[
            "research_ready_package"
        ],
        "commit_sha": commit_sha,
    }


# ======================================================================
# WORKFLOW STATUS
# ======================================================================

@router.get(
    "/workflow/strategies/{strategy_slug}/v{version}",
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
        "status": strategy.get(
            "status"
        ),
        "workflow": stage_snapshot(
            strategy
        ),
        "training_state": strategy.get(
            "training_state"
        ),
        "validation_state": strategy.get(
            "validation_state"
        ),
        "testing_state": strategy.get(
            "testing_state"
        ),
        "execution_state": strategy.get(
            "execution_state"
        ),
        "assessment_state": strategy.get(
            "assessment_state"
        ),
        "research_ready": strategy.get(
            "research_ready",
            False,
        ),
    }