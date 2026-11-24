
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 23 23:33:44 2026

@author: mohak
"""

from __future__ import annotations

from typing import Any, Literal


ResearchAction = Literal[
    "new_research",
    "follow_up",
    "clarification_required",
]


def _has_saved_result_stages(evidence: dict[str, Any]) -> bool:
    """
    Confirm that evidence contains substantive saved output
    from at least the development stage.

    The current research executor always evaluates development.
    Validation and final holdout may be absent for development-only runs.
    """

    stages = evidence.get("stages")

    if not isinstance(stages, dict):
        return False

    development = stages.get("development")

    if not isinstance(development, dict) or not development:
        return False

    # These fields are populated by the existing _compact_evidence()
    # function from the deterministic executor's saved stage output.
    evidence_fields = (
        "summary",
        "performance",
        "diagnostics",
        "random_baseline",
    )

    for field in evidence_fields:
        value = development.get(field)

        if isinstance(value, dict) and value:
            return True

        if isinstance(value, list) and value:
            return True

    warnings = development.get("warnings")

    if isinstance(warnings, list) and warnings:
        return True

    return False


def resolve_research_action(
    *,
    classifier_action: str,
    referenced_experiment_id: str | None,
    experiments: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Resolve the model's classification against real session experiments.

    A follow-up requires:
    - A matching experiment in the current session.
    - Completed execution.
    - Explicit approval.
    - A saved ResearchRequest.
    - Substantive saved development-stage evidence.
    """

    if classifier_action == "new_research":
        return {
            "research_action": "new_research",
            "referenced_experiment_id": None,
            "prior_research_request": None,
            "evidence_summary": None,
            "clarification_question": None,
        }

    if classifier_action == "ambiguous":
        return {
            "research_action": "clarification_required",
            "referenced_experiment_id": None,
            "prior_research_request": None,
            "evidence_summary": None,
            "clarification_question": (
                "Do you want to start a different, independent experiment, "
                "or improve one of your previous experiments? If you want "
                "an improvement, which experiment should we build on?"
            ),
        }

    if classifier_action != "follow_up":
        return {
            "research_action": "clarification_required",
            "referenced_experiment_id": None,
            "prior_research_request": None,
            "evidence_summary": None,
            "clarification_question": (
                "Should this be a new independent experiment, or a "
                "follow-up improvement to a previous experiment?"
            ),
        }

    reference = str(referenced_experiment_id or "").strip()

    if not reference:
        return {
            "research_action": "clarification_required",
            "referenced_experiment_id": None,
            "prior_research_request": None,
            "evidence_summary": None,
            "clarification_question": (
                "Which previous experiment do you want to improve? "
                "You can provide its experiment ID. Or tell me if this "
                "is a completely new experiment."
            ),
        }

    matches = []

    for experiment in experiments:
        experiment_id = str(
            experiment.get("experiment_id") or ""
        ).strip()

        ledger_id = str(
            experiment.get("ledger_id") or ""
        ).strip()

        if reference in {experiment_id, ledger_id}:
            matches.append(experiment)

    if len(matches) != 1:
        return {
            "research_action": "clarification_required",
            "referenced_experiment_id": None,
            "prior_research_request": None,
            "evidence_summary": None,
            "clarification_question": (
                f"I couldn't identify a completed experiment matching "
                f"'{reference}' in this chat. Do you want to start a new "
                "experiment, or provide the ID of the experiment you "
                "want to improve?"
            ),
        }

    matched = matches[0]

    if matched.get("status") != "completed":
        return {
            "research_action": "clarification_required",
            "referenced_experiment_id": None,
            "prior_research_request": None,
            "evidence_summary": None,
            "clarification_question": (
                "That experiment has not completed successfully. "
                "Only completed experiments can be used as a follow-up "
                "baseline. Would you like to start a new experiment?"
            ),
        }

    if matched.get("approval_status") != "approved":
        return {
            "research_action": "clarification_required",
            "referenced_experiment_id": None,
            "prior_research_request": None,
            "evidence_summary": None,
            "clarification_question": (
                "That experiment does not have an approved execution "
                "record. Please select a completed, approved experiment "
                "or start a new experiment."
            ),
        }

    prior_request = matched.get("prior_research_request")
    evidence = matched.get("evidence_summary")
    experiment_id = matched.get("experiment_id")

    if not isinstance(prior_request, dict) or not prior_request:
        return {
            "research_action": "clarification_required",
            "referenced_experiment_id": None,
            "prior_research_request": None,
            "evidence_summary": None,
            "clarification_question": (
                "I found that experiment, but its original validated "
                "configuration is unavailable. Please start a new "
                "experiment rather than building on incomplete context."
            ),
        }

    if not isinstance(evidence, dict) or not _has_saved_result_stages(
        evidence
    ):
        return {
            "research_action": "clarification_required",
            "referenced_experiment_id": None,
            "prior_research_request": None,
            "evidence_summary": None,
            "clarification_question": (
                "I found that experiment, but its saved result-stage "
                "evidence is incomplete. I can't safely design a "
                "follow-up from it. Would you like to start a new "
                "experiment?"
            ),
        }

    return {
        "research_action": "follow_up",
        "referenced_experiment_id": str(experiment_id),
        "prior_research_request": prior_request,
        "evidence_summary": evidence,
        "clarification_question": None,
    }


def build_experiment_context(
    ledger_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Convert research_ledger rows into compact, trusted session context.

    Only completed, approved experiments with a saved request and
    substantive development-stage evidence are eligible.
    """

    available: list[dict[str, Any]] = []

    for row in ledger_rows:
        if row.get("status") != "completed":
            continue

        if row.get("approval_status") != "approved":
            continue

        evidence = row.get("evidence_summary")
        proposal = row.get("proposal")

        if not isinstance(evidence, dict):
            continue

        if not isinstance(proposal, dict):
            continue

        experiment_id = evidence.get("experiment_id")

        if not isinstance(experiment_id, str) or not experiment_id.strip():
            continue

        prior_request = proposal.get("research_request")

        if not isinstance(prior_request, dict) or not prior_request:
            continue

        if not _has_saved_result_stages(evidence):
            continue

        available.append({
            "ledger_id": str(row.get("id") or ""),
            "experiment_id": experiment_id,
            "hypothesis": str(row.get("hypothesis") or ""),
            "status": "completed",
            "approval_status": "approved",
            "prior_research_request": prior_request,
            "evidence_summary": evidence,
        })

    return available
