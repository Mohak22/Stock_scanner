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


def resolve_research_action(
    *,
    classifier_action: str,
    referenced_experiment_id: str | None,
    experiments: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Resolve the model's classification against real session experiments.

    The model cannot create or invent an experiment reference.
    A follow-up requires a matching saved experiment, evidence and
    a complete previous ResearchRequest.
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

    if not isinstance(evidence, dict) or not evidence:
        return {
            "research_action": "clarification_required",
            "referenced_experiment_id": None,
            "prior_research_request": None,
            "evidence_summary": None,
            "clarification_question": (
                "I found that experiment, but its result evidence is "
                "unavailable. I can't safely design a follow-up from it. "
                "Would you like to start a new experiment?"
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

    Only rows with a saved experiment ID and evidence are eligible.
    """

    available: list[dict[str, Any]] = []

    for row in ledger_rows:
        evidence = row.get("evidence_summary") or {}
        proposal = row.get("proposal") or {}

        if not isinstance(evidence, dict):
            continue

        if not isinstance(proposal, dict):
            continue

        experiment_id = evidence.get("experiment_id")

        if not experiment_id:
            continue

        # Support the two likely proposal field names, but do not
        # manufacture a request if neither is present.
        prior_request = (
            proposal.get("research_request")
            or proposal.get("base_research_request")
        )

        if not isinstance(prior_request, dict):
            continue

        available.append({
            "ledger_id": str(row.get("id") or ""),
            "experiment_id": str(experiment_id),
            "hypothesis": str(row.get("hypothesis") or ""),
            "status": str(row.get("status") or ""),
            "approval_status": str(
                row.get("approval_status") or ""
            ),
            "prior_research_request": prior_request,
            "evidence_summary": evidence,
        })

    return available