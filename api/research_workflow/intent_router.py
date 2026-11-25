
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 23 23:33:44 2026

@author: mohak
"""

from __future__ import annotations

from typing import Any


def _has_saved_result_stages(evidence: dict[str, Any]) -> bool:
    """Return True only when substantive development evidence exists."""

    stages = evidence.get("stages")

    if not isinstance(stages, dict):
        return False

    development = stages.get("development")

    if not isinstance(development, dict) or not development:
        return False

    for field in (
        "summary",
        "performance",
        "diagnostics",
        "random_baseline",
    ):
        value = development.get(field)

        if isinstance(value, (dict, list)) and value:
            return True

    warnings = development.get("warnings")

    return isinstance(warnings, list) and bool(warnings)


def _empty_resolution(
    action: str,
    question: str | None = None,
) -> dict[str, Any]:
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
    """Match either a Ledger ID or a saved experiment ID."""

    normalized = str(reference or "").strip().lower()

    if not normalized:
        return []

    matches = []

    for item in experiments:
        identifiers = {
            str(item.get("experiment_id") or "").strip().lower(),
            str(item.get("ledger_id") or "").strip().lower(),
        }

        identifiers.discard("")

        if normalized in identifiers:
            matches.append(item)

    return matches


def resolve_research_action(
    *,
    classifier_action: str,
    referenced_experiment_id: str | None,
    experiments: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Resolve the user's request into one of three distinct workflows.

    new_research:
        Independent experiment; no previous configuration is inherited.

    revise_proposal:
        Reuse a previous proposal configuration. Evidence is not required.

    follow_up:
        Build on a completed, approved experiment with saved evidence.
    """

    if classifier_action == "new_research":
        return _empty_resolution("new_research")

    if classifier_action not in {
        "revise_proposal",
        "follow_up",
    }:
        return _empty_resolution(
            "clarification_required",
            (
                "Would you like to start a new, different independent "
                "experiment, or modify an existing proposal? "
                "You can also provide the Ledger ID."
            ),
        )

    reference = str(referenced_experiment_id or "").strip()

    matches = (
        _match_reference(reference, experiments)
        if reference
        else []
    )

    # A revision without an explicit ID may use the newest revisable
    # proposal because the user's intent is already explicit.
    if (
        not reference
        and classifier_action == "revise_proposal"
    ):
        candidates = [
            item
            for item in experiments
            if item.get("can_revise")
        ]

        if candidates:
            matches = [candidates[0]]

    # Follow-ups must identify a particular completed experiment.
    if len(matches) != 1:
        choices = []

        for item in experiments[:5]:
            choices.append(
                f"- Ledger ID: {item.get('ledger_id')} | "
                f"Status: {item.get('status')} | "
                f"Hypothesis: {item.get('hypothesis', '')}"
            )

        choices_text = (
            "\n".join(choices)
            if choices
            else "No proposals were found in this chat."
        )

        if classifier_action == "follow_up" and not reference:
            question = (
                "Which previous experiment should this follow-up use? "
                "Please provide its Ledger ID or experiment ID.\n\n"
                f"{choices_text}"
            )
        else:
            question = (
                "I couldn't identify exactly which proposal you mean. "
                "Please reply with its Ledger ID, for example:\n"
                "'Revise proposal <Ledger ID>'.\n\n"
                f"{choices_text}\n\n"
                "You can also say 'use the latest proposal' "
                "if you want to revise the newest one."
            )

        return _empty_resolution(
            "clarification_required",
            question,
        )

    matched = matches[0]

    prior_request = matched.get("prior_research_request")

    if (
        not isinstance(prior_request, dict)
        or not prior_request
    ):
        return _empty_resolution(
            "clarification_required",
            (
                "I found the proposal, but its original validated "
                "configuration is unavailable. I cannot safely "
                "revise it without that configuration."
            ),
        )

    experiment_id = matched.get("experiment_id")
    ledger_id = matched.get("ledger_id")

    # ------------------------------------------------------------
    # Proposal revision: no completed evidence is required.
    # ------------------------------------------------------------

    if classifier_action == "revise_proposal":

        if not matched.get("can_revise"):
            return _empty_resolution(
                "clarification_required",
                (
                    "This proposal cannot currently be revised because "
                    "its original configuration is unavailable."
                ),
            )

        return {
            "research_action": "revise_proposal",
            "referenced_experiment_id": experiment_id,
            "referenced_ledger_id": ledger_id,
            "prior_research_request": prior_request,
            "evidence_summary": None,
            "clarification_question": None,
        }

    # ------------------------------------------------------------
    # Scientific follow-up: completed evidence is mandatory.
    # ------------------------------------------------------------

    if matched.get("status") != "completed":
        return _empty_resolution(
            "clarification_required",
            (
                "This proposal has not completed successfully. "
                "I can revise its configuration, but I cannot use it "
                "as completed research evidence. "
                "Say 'revise this proposal' to modify it."
            ),
        )

    if matched.get("approval_status") != "approved":
        return _empty_resolution(
            "clarification_required",
            (
                "This experiment does not have an approved execution "
                "record, so it cannot be used for a scientific follow-up."
            ),
        )

    evidence = matched.get("evidence_summary")

    if (
        not isinstance(evidence, dict)
        or not _has_saved_result_stages(evidence)
    ):
        return _empty_resolution(
            "clarification_required",
            (
                "The experiment's saved evidence is incomplete. "
                "A follow-up requires substantive completed research "
                "results."
            ),
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
    """
    Build the compact experiment context used by the conversational
    router.

    Pending, failed and rejected proposals remain visible because
    they may be revised.

    Only completed, approved experiments with substantive evidence
    are eligible for scientific follow-ups.
    """

    available = []

    for row in ledger_rows:

        proposal = row.get("proposal")
        evidence = row.get("evidence_summary")

        if not isinstance(proposal, dict):
            continue

        if not isinstance(evidence, dict):
            evidence = {}

        prior_request = proposal.get("research_request")

        if (
            not isinstance(prior_request, dict)
            or not prior_request
        ):
            continue

        ledger_id = str(row.get("id") or "").strip()

        if not ledger_id:
            continue

        experiment_id = evidence.get("experiment_id")

        if experiment_id is not None:
            experiment_id = str(experiment_id).strip() or None

        status = str(row.get("status") or "proposed").lower()

        approval_status = str(
            row.get("approval_status") or "pending"
        ).lower()

        has_evidence = _has_saved_result_stages(evidence)

        can_follow_up = (
            status == "completed"
            and approval_status == "approved"
            and has_evidence
            and experiment_id is not None
        )

        available.append({
            "ledger_id": ledger_id,
            "experiment_id": experiment_id,
            "hypothesis": str(row.get("hypothesis") or ""),
            "status": status,
            "approval_status": approval_status,
            "prior_research_request": prior_request,
            "evidence_summary": (
                evidence if can_follow_up else None
            ),
            "can_revise": True,
            "can_follow_up": can_follow_up,
        })

    # Database query is newest-first. Preserve that order.
    return available
