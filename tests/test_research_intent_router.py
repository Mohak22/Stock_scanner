
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 23 23:35:27 2026

@author: mohak
"""

from api.research_workflow.intent_router import (
    build_experiment_context,
    resolve_research_action,
)
from api.research_workflow.designer import (
    build_designer_system_prompt,
)


def sample_evidence():
    return {
        "experiment_id": "EXP-001",
        "stages": {
            "development": {
                "summary": {"sample_size": 120},
                "performance": {"mean_return": 0.01},
                "diagnostics": {},
                "random_baseline": {},
                "warnings": [],
            },
            "validation": None,
            "final_holdout": None,
        },
    }


def sample_experiment():
    return {
        "ledger_id": "ledger-001",
        "experiment_id": "EXP-001",
        "hypothesis": "RSI below 30 predicts positive next-day returns",
        "status": "completed",
        "approval_status": "approved",
        "can_revise": True,
        "can_follow_up": True,
        "prior_research_request": {
            "development_start": "2024-01-01",
            "development_end": "2024-12-31",
            "evaluation_horizons": [1, 3, 5],
        },
        "evidence_summary": sample_evidence(),
    }


def sample_ledger_row(**overrides):
    row = {
        "id": "ledger-001",
        "hypothesis": "Test hypothesis",
        "status": "completed",
        "approval_status": "approved",
        "proposal": {
            "research_request": {
                "development_start": "2024-01-01",
                "development_end": "2024-12-31",
                "evaluation_horizons": [1, 3, 5],
            }
        },
        "evidence_summary": sample_evidence(),
    }

    row.update(overrides)
    return row


def test_explicit_new_research_does_not_use_previous_experiment():
    result = resolve_research_action(
        classifier_action="new_research",
        referenced_experiment_id=None,
        experiments=[sample_experiment()],
    )

    assert result["research_action"] == "new_research"
    assert result["prior_research_request"] is None
    assert result["evidence_summary"] is None


def test_valid_follow_up_uses_matching_experiment():
    result = resolve_research_action(
        classifier_action="follow_up",
        referenced_experiment_id="EXP-001",
        experiments=[sample_experiment()],
    )

    assert result["research_action"] == "follow_up"
    assert result["referenced_experiment_id"] == "EXP-001"
    assert result["referenced_ledger_id"] == "ledger-001"
    assert result["prior_research_request"] is not None
    assert result["evidence_summary"] is not None


def test_valid_revision_uses_previous_configuration_without_evidence():
    result = resolve_research_action(
        classifier_action="revise_proposal",
        referenced_experiment_id="ledger-001",
        experiments=[sample_experiment()],
    )

    assert result["research_action"] == "revise_proposal"
    assert result["referenced_experiment_id"] == "EXP-001"
    assert result["referenced_ledger_id"] == "ledger-001"
    assert result["prior_research_request"] is not None
    assert result["evidence_summary"] is None


def test_revision_without_reference_uses_latest_revisable_proposal():
    experiments = [
        {
            **sample_experiment(),
            "ledger_id": "ledger-newest",
            "experiment_id": "EXP-NEWEST",
        },
        {
            **sample_experiment(),
            "ledger_id": "ledger-older",
            "experiment_id": "EXP-OLDER",
        },
    ]

    result = resolve_research_action(
        classifier_action="revise_proposal",
        referenced_experiment_id=None,
        experiments=experiments,
    )

    assert result["research_action"] == "revise_proposal"
    assert result["referenced_ledger_id"] == "ledger-newest"
    assert result["referenced_experiment_id"] == "EXP-NEWEST"


def test_ambiguous_request_asks_user_to_choose():
    result = resolve_research_action(
        classifier_action="ambiguous",
        referenced_experiment_id=None,
        experiments=[sample_experiment()],
    )

    assert result["research_action"] == "clarification_required"
    assert "independent experiment" in (
        result["clarification_question"]
    )
    assert "modify" in result["clarification_question"]


def test_unknown_experiment_reference_is_rejected():
    result = resolve_research_action(
        classifier_action="follow_up",
        referenced_experiment_id="EXP-999",
        experiments=[sample_experiment()],
    )

    assert result["research_action"] == "clarification_required"


def test_follow_up_without_reference_asks_for_id():
    result = resolve_research_action(
        classifier_action="follow_up",
        referenced_experiment_id=None,
        experiments=[sample_experiment()],
    )

    assert result["research_action"] == "clarification_required"
    assert "Ledger ID" in result["clarification_question"]


def test_context_requires_saved_request():
    rows = [
        sample_ledger_row(),
        sample_ledger_row(
            id="ledger-002",
            proposal={},
        ),
    ]

    result = build_experiment_context(rows)

    assert len(result) == 1
    assert result[0]["experiment_id"] == "EXP-001"


def test_pending_proposal_remains_available_for_revision():
    result = build_experiment_context([
        sample_ledger_row(status="proposed")
    ])

    assert len(result) == 1
    assert result[0]["can_revise"] is True
    assert result[0]["can_follow_up"] is False
    assert result[0]["evidence_summary"] is None


def test_failed_proposal_remains_available_for_revision():
    result = build_experiment_context([
        sample_ledger_row(status="failed")
    ])

    assert len(result) == 1
    assert result[0]["can_revise"] is True
    assert result[0]["can_follow_up"] is False
    assert result[0]["evidence_summary"] is None


def test_rejected_proposal_remains_available_for_revision():
    result = build_experiment_context([
        sample_ledger_row(approval_status="rejected")
    ])

    assert len(result) == 1
    assert result[0]["can_revise"] is True
    assert result[0]["can_follow_up"] is False


def test_unapproved_proposal_remains_available_for_revision():
    result = build_experiment_context([
        sample_ledger_row(approval_status="pending")
    ])

    assert len(result) == 1
    assert result[0]["can_revise"] is True
    assert result[0]["can_follow_up"] is False


def test_experiment_without_stages_remains_revision_candidate():
    evidence = {"experiment_id": "EXP-001"}

    result = build_experiment_context([
        sample_ledger_row(evidence_summary=evidence)
    ])

    assert len(result) == 1
    assert result[0]["can_revise"] is True
    assert result[0]["can_follow_up"] is False
    assert result[0]["evidence_summary"] is None


def test_experiment_with_empty_development_stage_remains_revision_candidate():
    evidence = {
        "experiment_id": "EXP-001",
        "stages": {
            "development": {},
            "validation": None,
            "final_holdout": None,
        },
    }

    result = build_experiment_context([
        sample_ledger_row(evidence_summary=evidence)
    ])

    assert len(result) == 1
    assert result[0]["can_revise"] is True
    assert result[0]["can_follow_up"] is False


def test_experiment_with_only_empty_stage_metrics_remains_revision_candidate():
    evidence = {
        "experiment_id": "EXP-001",
        "stages": {
            "development": {
                "summary": {},
                "performance": {},
                "diagnostics": {},
                "random_baseline": {},
                "warnings": [],
            },
        },
    }

    result = build_experiment_context([
        sample_ledger_row(evidence_summary=evidence)
    ])

    assert len(result) == 1
    assert result[0]["can_revise"] is True
    assert result[0]["can_follow_up"] is False


def test_follow_up_rejects_incomplete_evidence():
    experiment = sample_experiment()
    experiment["evidence_summary"] = {
        "experiment_id": "EXP-001",
        "stages": {},
    }

    result = resolve_research_action(
        classifier_action="follow_up",
        referenced_experiment_id="EXP-001",
        experiments=[experiment],
    )

    assert result["research_action"] == "clarification_required"


def test_follow_up_rejects_unapproved_experiment():
    experiment = sample_experiment()
    experiment["approval_status"] = "pending"

    result = resolve_research_action(
        classifier_action="follow_up",
        referenced_experiment_id="EXP-001",
        experiments=[experiment],
    )

    assert result["research_action"] == "clarification_required"


def test_follow_up_rejects_non_completed_experiment():
    experiment = sample_experiment()
    experiment["status"] = "failed"

    result = resolve_research_action(
        classifier_action="follow_up",
        referenced_experiment_id="EXP-001",
        experiments=[experiment],
    )

    assert result["research_action"] == "clarification_required"


def test_initial_revision_and_follow_up_prompts_are_separate():
    initial = build_designer_system_prompt("initial")
    revision = build_designer_system_prompt("revision")
    follow_up = build_designer_system_prompt("follow_up")

    assert "new, independent" in initial
    assert "prior_research_request" not in initial

    assert "prior_research_request" in revision
    assert "evidence_summary" not in revision

    assert "prior_research_request" in follow_up
    assert "evidence_summary" in follow_up
