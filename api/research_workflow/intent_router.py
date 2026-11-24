
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 23 23:33:44 2026

@author: mohak
"""

from __future__ import annotations

from typing import Any, Literal


ResearchAction = Literal[
    "new_research",
    "revise_proposal",
    "follow_up",
    "clarification_required",
]


def _has_saved_result_stages(evidence: dict[str, Any]) -> bool:
    stages = evidence.get("stages")
    if not isinstance(stages, dict):
        return False

    development = stages.get("development")
    if not isinstance(development, dict) or not development:
        return False

    for field in ("summary", "performance", "diagnostics", "random_baseline"):
        value = development.get(field)
        if isinstance(value, (dict, list)) and value:
            return True

    warnings = development.get("warnings")
    return isinstance(warnings, list) and bool(warnings)


def _empty_resolution(action: str, question: str | None = None) -> dict:
    return {
        "research_action": action,
        "referenced_experiment_id": None,
        "referenced_ledger_id": None,
        "prior_research_request": None,
        "evidence_summary": None,
        "clarification_question": question,
    }


def _match_reference(
    reference: str,
    experiments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    reference = str(reference or "").strip().lower()
    if not reference:
        return []

    matches = []

    for item in experiments:
        identifiers = {
            str(item.get("experiment_id") or "").strip().lower(),
            str(item.get("ledger_id") or "").strip().lower(),
        }

        if reference in identifiers:
            matches.append(item)

    return matches


def resolve_research_action(
    *,
    classifier_action: str,
    referenced_experiment_id: str | None,
    experiments: list[dict[str, Any]],
) -> dict[str, Any]:

    if classifier_action == "new_research":
        return _empty_resolution("new_research")

    if classifier_action not in {"revise_proposal", "follow_up"}:
        return _empty_resolution(
            "clarification_required",
            (
                "Would you like to start a new independent experiment, "
                "or modify the most recent proposal? You can also provide "
                "the Ledger ID shown on the proposal card."
            ),
        )

    reference = str(referenced_experiment_id or "").strip()
    matches = _match_reference(reference, experiments) if reference else []

    # If the user clearly asks to revise the previous proposal but
    # provides no ID, use the latest proposal in this chat.
    if not reference and classifier_action == "revise_proposal":
        candidates = [
            item for item in experiments
            if item.get("can_revise")
        ]
        if candidates:
            matches = [candidates[0]]

    if len(matches) != 1:
        choices = []
        for item in experiments[:5]:
            choices.append(
                f"- Ledger ID: {item.get('ledger_id')} | "
                f"Status: {item.get('status')} | "
                f"Hypothesis: {item.get('hypothesis', '')}"
            )

        choices_text = "\n".join(choices) or "No proposals were found."

        return _empty_resolution(
            "clarification_required",
            (
                "I couldn't identify which proposal you mean. "
                "You can reply with the Ledger ID shown below, for example: "
                "'Revise proposal <Ledger ID>'.\n\n"
                f"{choices_text}\n\n"
                "Or say 'use the latest proposal'."
            ),
        )

    matched = matches[0]
    prior_request = matched.get("prior_research_request")

    if not isinstance(prior_request, dict) or not prior_request:
        return _empty_resolution(
            "clarification_required",
            "I found the proposal, but its original configuration is unavailable.",
        )

    experiment_id = matched.get("experiment_id")
    ledger_id = matched.get("ledger_id")
    evidence = matched.get("evidence_summary")

    if classifier_action == "revise_proposal":
        return {
            "research_action": "revise_proposal",
            "referenced_experiment_id": experiment_id,
            "referenced_ledger_id": ledger_id,
            "prior_research_request": prior_request,
            "evidence_summary": None,
            "clarification_question": None,
        }

    # A scientific follow-up is different: it requires actual completed
    # evidence and must never use a failed proposal as factual evidence.
    if matched.get("status") != "completed":
        return _empty_resolution(
            "clarification_required",
            (
                "This proposal has not completed successfully. I can revise "
                "its configuration, but I cannot use it as completed "
                "research evidence. Say 'revise this proposal' to modify it."
            ),
        )

    if matched.get("approval_status") != "approved":
        return _empty_resolution(
            "clarification_required",
            "The experiment does not have an approved execution record.",
        )

    if not isinstance(evidence, dict) or not _has_saved_result_stages(evidence):
        return _empty_resolution(
            "clarification_required",
            "The experiment's saved result evidence is incomplete.",
        )

    return {
        "research_action": "follow_up",
        "referenced_experiment_id": experiment_id,
        "referenced_ledger_id": ledger_id,
        "prior_research_request": prior_request,
        "evidence_summary": evidence,
        "clarification_question": None,
    }


def build_experiment_context(
    ledger_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    available = []

    for row in ledger_rows:
        proposal = row.get("proposal") or {}
        evidence = row.get("evidence_summary") or {}

        if not isinstance(proposal, dict):
            continue

        prior_request = proposal.get("research_request")
        if not isinstance(prior_request, dict) or not prior_request:
            continue

        experiment_id = evidence.get("experiment_id")
        status = str(row.get("status") or "proposed")
        approval_status = str(row.get("approval_status") or "pending")

        can_follow_up = (
            status == "completed"
            and approval_status == "approved"
            and isinstance(evidence, dict)
            and _has_saved_result_stages(evidence)
        )

        available.append({
            "ledger_id": str(row.get("id") or ""),
            "experiment_id": experiment_id,
            "hypothesis": str(row.get("hypothesis") or ""),
            "status": status,
            "approval_status": approval_status,
            "prior_research_request": prior_request,
            "evidence_summary": evidence if can_follow_up else None,
            "can_revise": True,
            "can_follow_up": can_follow_up,
        })

    # The database query orders newest first; preserve that order.
    return available
