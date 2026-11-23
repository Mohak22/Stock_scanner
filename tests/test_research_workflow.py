# -*- coding: utf-8 -*-
"""
Created on Mon Nov 23 17:33:50 2026

@author: mohak
"""

from api.research_workflow.designer import ResearchDesignerOutput
from api.research_workflow.graph import (
    build_research_graph,
    run_follow_up_research_design,
)


def fake_clarification_designer(**kwargs):
    return (
        ResearchDesignerOutput(
            status="needs_clarification",
            assistant_message="Which historical date range should we use?",
        ),
        {"provider": "test", "total_tokens": 0},
    )


def valid_request():
    return {
        "development_start": "2022-01-01",
        "development_end": "2023-12-31",
        "universe": {"type": "all_stocks"},
        "features": [
            {
                "type": "rsi",
                "parameters": {"period": 14},
            },
        ],
        "entry_conditions": [
            {
                "left": {
                    "feature": "rsi",
                    "parameters": {"period": 14},
                },
                "operator": "<",
                "right": {"value": 30},
            },
        ],
        "evaluation_horizons": [1, 3, 5],
    }


def fake_valid_designer(**kwargs):
    return (
        ResearchDesignerOutput(
            status="proposal",
            assistant_message=(
                "I propose testing whether RSI below 30 "
                "is associated with stronger forward returns."
            ),
            research_question=(
                "Does RSI below 30 identify stocks with "
                "stronger forward returns?"
            ),
            hypothesis=(
                "Stocks with RSI below 30 have higher subsequent returns."
            ),
            research_request=valid_request(),
        ),
        {"provider": "test", "total_tokens": 0},
    )


def fake_invalid_designer(**kwargs):
    request = valid_request()
    request["features"][0]["type"] = "made_up_feature"
    request["entry_conditions"][0]["left"]["feature"] = "made_up_feature"

    return (
        ResearchDesignerOutput(
            status="proposal",
            assistant_message="Testing invalid feature handling.",
            research_question="Can an invalid feature pass?",
            hypothesis="It should not pass validation.",
            research_request=request,
        ),
        {"provider": "test", "total_tokens": 0},
    )


def test_graph_stops_for_clarification():
    graph = build_research_graph(
        designer_function=fake_clarification_designer,
    )

    result = graph.invoke({
        "session_id": "test-session",
        "user_message": "Test hypothesis",
        "conversation_history": [],
    })

    assert result["status"] == "needs_clarification"
    assert "date range" in result["assistant_message"]
    assert result["validated_request"] is None


def test_graph_validates_supported_research_request():
    graph = build_research_graph(
        designer_function=fake_valid_designer,
    )

    result = graph.invoke({
        "session_id": "test-session",
        "user_message": "Test RSI hypothesis",
        "conversation_history": [],
    })

    assert result["status"] == "proposal_validated"
    assert result["validated_request"] is not None
    assert result["validation_errors"] == []
    assert result["validated_request"]["features"][0]["type"] == "rsi"


def test_graph_rejects_unsupported_feature():
    graph = build_research_graph(
        designer_function=fake_invalid_designer,
    )

    result = graph.invoke({
        "session_id": "test-session",
        "user_message": "Test invalid feature",
        "conversation_history": [],
    })

    assert result["status"] == "validation_failed"
    assert result["validated_request"] is None
    assert result["validation_errors"]


def test_follow_up_requires_previous_request_and_evidence():
    try:
        run_follow_up_research_design(
            session_id="test-session",
            user_message="Test a volume improvement",
            prior_research_request=valid_request(),
            evidence_summary={},
            designer_function=fake_valid_designer,
        )
    except ValueError as exc:
        assert "evidence summary" in str(exc).lower()
    else:
        raise AssertionError("Expected missing evidence to be rejected.")


def test_follow_up_passes_previous_context_to_designer():
    captured = {}

    def fake_follow_up_designer(**kwargs):
        captured.update(kwargs)

        return (
            ResearchDesignerOutput(
                status="proposal",
                assistant_message=(
                    "Test the existing RSI setup with an additional "
                    "volume confirmation."
                ),
                research_question=(
                    "Does volume confirmation improve the RSI setup?"
                ),
                hypothesis=(
                    "RSI signals with stronger relative volume "
                    "produce better forward returns."
                ),
                research_request=valid_request(),
            ),
            {"provider": "test", "total_tokens": 0},
        )

    prior_request = valid_request()
    evidence = {
        "experiment_id": "EXP-TEST-001",
        "sample_size": 120,
        "summary": "Illustrative test evidence only.",
    }

    result = run_follow_up_research_design(
        session_id="test-session",
        user_message="Try adding a volume confirmation.",
        prior_research_request=prior_request,
        evidence_summary=evidence,
        previous_experiment_id="EXP-TEST-001",
        designer_function=fake_follow_up_designer,
    )

    assert result["status"] == "proposal_validated"
    assert captured["design_mode"] == "follow_up"
    assert captured["prior_research_request"] == prior_request
    assert captured["evidence_summary"] == evidence
    assert captured["previous_experiment_id"] == "EXP-TEST-001"
