
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 24 07:48:25 2026

@author: mohak
"""

from uuid import UUID

import pytest
from fastapi import HTTPException

from api.research_assistant import conversation


SESSION_ID = UUID("11111111-1111-4111-8111-111111111111")
MESSAGE_ID = "test-message-001"


def valid_request():
    return {
        "development_start": "2022-01-01",
        "development_end": "2023-12-31",
        "universe": {"type": "all_stocks"},
        "features": [
            {"type": "rsi", "parameters": {"period": 14}},
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


class FakeResponse:
    def __init__(self, data=None):
        self.data = data if data is not None else []


class FakeQuery:
    def __init__(self, db, table):
        self.db = db
        self.table_name = table
        self.operation = "select"
        self.payload = None
        self.filters = {}
        self.limit_value = None
        self.selected_columns = None

    def select(self, columns="*", **kwargs):
        self.operation = "select"
        self.selected_columns = columns
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def eq(self, key, value):
        self.filters[key] = ("eq", value)
        return self

    def contains(self, key, value):
        self.filters[key] = ("contains", value)
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def order(self, *args, **kwargs):
        return self

    def execute(self):
        rows = self.db.tables.setdefault(self.table_name, [])

        if self.operation == "insert":
            payloads = (
                self.payload
                if isinstance(self.payload, list)
                else [self.payload]
            )

            inserted = []

            for payload in payloads:
                row = dict(payload)
                rows.append(row)
                inserted.append(row)

                self.db.inserts.setdefault(
                    self.table_name, []
                ).append(row)

            return FakeResponse(inserted)

        if self.operation == "update":
            self.db.updates.setdefault(
                self.table_name, []
            ).append({
                "payload": self.payload,
                "filters": self.filters,
            })

            return FakeResponse([])

        matched = []

        for row in rows:
            include = True

            for key, (operator, expected) in self.filters.items():
                actual = row.get(key)

                if operator == "eq" and actual != expected:
                    include = False
                    break

                if operator == "contains":
                    if not isinstance(actual, dict):
                        include = False
                        break

                    if not all(
                        actual.get(k) == v
                        for k, v in expected.items()
                    ):
                        include = False
                        break

            if include:
                matched.append(row)

        if self.limit_value is not None:
            matched = matched[:self.limit_value]

        if self.selected_columns and self.selected_columns != "*":
            columns = [
                column.strip()
                for column in self.selected_columns.split(",")
            ]

            matched = [
                {
                    key: row[key]
                    for key in columns
                    if key in row
                }
                for row in matched
            ]

        return FakeResponse(matched)


class FakeRPCQuery:
    """Simulates the idempotent PostgreSQL proposal RPC."""

    def __init__(self, db, function_name, params):
        self.db = db
        self.function_name = function_name
        self.params = params

    def execute(self):
        self.db.rpc_calls.append({
            "function_name": self.function_name,
            "params": self.params,
        })

        if self.db.rpc_error is not None:
            raise self.db.rpc_error

        if (
            self.function_name
            != "persist_langgraph_proposal_idempotent"
        ):
            raise ValueError(
                f"Unexpected RPC function: {self.function_name}"
            )

        p = self.params
        client_message_id = p["p_client_message_id"]

        # Simulate idempotent reuse of an existing proposal.
        for existing_run in self.db.tables.get("agent_runs", []):
            existing_input = existing_run.get("input_data") or {}

            if (
                existing_run["session_id"] == p["p_session_id"]
                and existing_input.get("client_message_id")
                == client_message_id
            ):
                existing_ledger = next(
                    (
                        ledger
                        for ledger in self.db.tables.get(
                            "research_ledger", []
                        )
                        if ledger["agent_run_id"] == existing_run["id"]
                    ),
                    None,
                )

                if existing_ledger is None:
                    raise RuntimeError(
                        "Existing agent run has no research ledger."
                    )

                return FakeResponse({
                    "agent_run_id": existing_run["id"],
                    "ledger_id": existing_ledger["id"],
                    "reused": True,
                })

        agent_run = {
            "id": p["p_run_id"],
            "session_id": p["p_session_id"],
            "thread_id": p["p_thread_id"],
            "status": "awaiting_approval",
            "current_step": "awaiting_human_approval",
            "provider": p["p_provider"],
            "model": p["p_model"],
            "tokens_used": p["p_tokens_used"],
            "input_data": p["p_input_data"],
            "output_data": p["p_output_data"],
            "started_at": p["p_started_at"],
        }

        ledger = {
            "id": f"ledger-test-{len(self.db.tables.get('research_ledger', [])) + 1:03d}",
            "session_id": p["p_session_id"],
            "agent_run_id": p["p_run_id"],
            "hypothesis": p["p_hypothesis"],
            "hypothesis_family": None,
            "status": "proposed",
            "approval_status": "pending",
            "proposal": p["p_proposal"],
            "decision": {},
            "evidence_summary": {},
        }

        self.db.tables.setdefault("agent_runs", []).append(agent_run)
        self.db.tables.setdefault("research_ledger", []).append(ledger)

        self.db.inserts.setdefault("agent_runs", []).append(agent_run)
        self.db.inserts.setdefault("research_ledger", []).append(ledger)

        return FakeResponse({
            "agent_run_id": p["p_run_id"],
            "ledger_id": ledger["id"],
            "reused": False,
        })


class FakeDB:
    def __init__(self):
        self.tables = {}
        self.inserts = {}
        self.updates = {}
        self.rpc_calls = []
        self.rpc_error = None

    def table(self, name):
        return FakeQuery(self, name)

    def rpc(self, function_name, params):
        return FakeRPCQuery(self, function_name, params)

    def seed(self, table, rows):
        self.tables.setdefault(table, []).extend(rows)


@pytest.fixture
def fake_environment(monkeypatch):
    db = FakeDB()

    monkeypatch.setattr(
        conversation,
        "get_supabase_client",
        lambda: db,
    )

    monkeypatch.setattr(
        conversation,
        "_get_active_session",
        lambda session_id: {
            "id": str(session_id),
            "status": "active",
        },
    )

    monkeypatch.setattr(
        conversation,
        "_load_recent_messages",
        lambda session_id: [
            {"role": "user", "content": "Test research"}
        ],
    )

    monkeypatch.setattr(
        conversation,
        "_load_session_experiments",
        lambda session_id: [],
    )

    return db


def routed_proposal(action="new_research", reference=None):
    return {
        "intent": "propose_experiment",
        "response": "I will design the experiment.",
        "needs_follow_up": False,
        "follow_up_question": "",
        "research_question": (
            "Does RSI below 30 identify stronger forward returns?"
        ),
        "hypothesis": (
            "Stocks with RSI below 30 have higher subsequent returns."
        ),
        "research_action": action,
        "referenced_experiment_id": reference,
    }


def routed_non_proposal():
    return {
        "intent": "general_conversation",
        "response": "Here is a general research explanation.",
        "needs_follow_up": False,
        "follow_up_question": "",
        "research_question": "",
        "hypothesis": "",
        "research_action": None,
        "referenced_experiment_id": None,
    }


def valid_workflow_result():
    return {
        "status": "proposal_validated",
        "assistant_message": "The configuration passed validation.",
        "research_question": (
            "Does RSI below 30 identify stronger forward returns?"
        ),
        "hypothesis": (
            "Stocks with RSI below 30 have higher subsequent returns."
        ),
        "rationale": (
            "Oversold RSI readings may identify short-term reversals."
        ),
        "expected_learning": (
            "Determine whether RSI below 30 is associated "
            "with stronger subsequent returns."
        ),
        "experiment_type": "threshold_sensitivity",
        "confidence": "medium",
        "validated_request": valid_request(),
        "validation_errors": [],
        "usage": {
            "provider": "test",
            "model": "fake-model",
            "total_tokens": 100,
        },
    }


def call_chat(
    client_message_id=MESSAGE_ID,
    message="Test this research hypothesis",
):
    return conversation.chat_with_research_assistant(
        session_id=SESSION_ID,
        request=conversation.ChatMessageRequest(
            message=message,
            client_message_id=client_message_id,
        ),
    )


def seed_user_message(
    db,
    client_message_id=MESSAGE_ID,
    content="Test this research hypothesis",
):
    db.seed(
        "chat_messages",
        [{
            "session_id": str(SESSION_ID),
            "role": "user",
            "content": content,
            "metadata": {
                "client_message_id": client_message_id,
            },
        }],
    )


def test_new_research_invokes_initial_graph_and_saves_pending_proposal(
    fake_environment,
    monkeypatch,
):
    db = fake_environment
    graph_calls = []

    monkeypatch.setattr(
        conversation,
        "_call_research_router",
        lambda *args: (
            routed_proposal("new_research"),
            {"provider": "test", "total_tokens": 10},
        ),
    )

    def fake_initial_graph(**kwargs):
        graph_calls.append(kwargs)
        return valid_workflow_result()

    monkeypatch.setattr(
        conversation,
        "run_initial_research_design",
        fake_initial_graph,
    )

    result = call_chat()

    assert len(graph_calls) == 1
    assert graph_calls[0]["session_id"] == str(SESSION_ID)

    assert result["workflow_status"] == "proposal_saved"
    assert result["agent_run_id"]
    assert result["ledger_id"] == "ledger-test-001"

    ledger_rows = db.inserts["research_ledger"]
    assert len(ledger_rows) == 1

    ledger = ledger_rows[0]
    assert ledger["status"] == "proposed"
    assert ledger["approval_status"] == "pending"

    saved_request = ledger["proposal"]["research_request"]

    assert saved_request["features"][0]["type"] == "rsi"
    assert saved_request["features"][0]["parameters"]["period"] == 14
    assert (
        saved_request["entry_conditions"][0]["left"]["feature"]
        == "rsi"
    )
    assert saved_request["entry_conditions"][0]["operator"] == "<"
    assert saved_request["entry_conditions"][0]["right"]["value"] == 30
    assert saved_request["evaluation_horizons"] == [1, 3, 5]

    agent_runs = db.tables["agent_runs"]
    assert len(agent_runs) == 1
    assert agent_runs[0]["status"] == "awaiting_approval"
    assert (
        agent_runs[0]["current_step"]
        == "awaiting_human_approval"
    )

    assert len(db.rpc_calls) == 1
    assert (
        db.rpc_calls[0]["function_name"]
        == "persist_langgraph_proposal_idempotent"
    )
    assert (
        db.rpc_calls[0]["params"]["p_client_message_id"]
        == MESSAGE_ID
    )

    assistant_messages = [
        row
        for row in db.inserts["chat_messages"]
        if row["role"] == "assistant"
    ]

    assert len(assistant_messages) == 1
    assert (
        assistant_messages[0]["metadata"]["client_message_id"]
        == MESSAGE_ID
    )
    assert "NOT been executed" in result["response"]


def test_ambiguous_request_does_not_invoke_graph_or_persist_proposal(
    fake_environment,
    monkeypatch,
):
    db = fake_environment

    monkeypatch.setattr(
        conversation,
        "_call_research_router",
        lambda *args: (
            routed_proposal("ambiguous"),
            {"provider": "test", "total_tokens": 10},
        ),
    )

    def unexpected_graph_call(**kwargs):
        pytest.fail("LangGraph must not run for an ambiguous request.")

    monkeypatch.setattr(
        conversation,
        "run_initial_research_design",
        unexpected_graph_call,
    )
    monkeypatch.setattr(
        conversation,
        "run_follow_up_research_design",
        unexpected_graph_call,
    )

    result = call_chat()

    assert result["needs_follow_up"] is True
    assert result["workflow_status"] is None
    assert result["agent_run_id"] is None
    assert result["ledger_id"] is None
    assert "independent experiment" in result["response"].lower()
    assert "research_ledger" not in db.inserts
    assert "agent_runs" not in db.inserts


def test_follow_up_invokes_graph_with_previous_experiment_context(
    fake_environment,
    monkeypatch,
):
    db = fake_environment
    graph_calls = []

    prior_request = valid_request()
    evidence = {
        "experiment_id": "EXP-TEST-001",
        "stages": {
            "development": {
                "summary": {"sample_size": 120},
            },
        },
    }

    monkeypatch.setattr(
        conversation,
        "_call_research_router",
        lambda *args: (
            routed_proposal("follow_up", "EXP-TEST-001"),
            {"provider": "test", "total_tokens": 10},
        ),
    )

    monkeypatch.setattr(
        conversation,
        "resolve_research_action",
        lambda **kwargs: {
            "research_action": "follow_up",
            "referenced_experiment_id": "EXP-TEST-001",
            "prior_research_request": prior_request,
            "evidence_summary": evidence,
            "clarification_question": None,
        },
    )

    def fake_follow_up_graph(**kwargs):
        graph_calls.append(kwargs)
        return valid_workflow_result()

    monkeypatch.setattr(
        conversation,
        "run_follow_up_research_design",
        fake_follow_up_graph,
    )

    result = call_chat()

    assert len(graph_calls) == 1
    assert graph_calls[0]["prior_research_request"] == prior_request
    assert graph_calls[0]["evidence_summary"] == evidence
    assert (
        graph_calls[0]["previous_experiment_id"]
        == "EXP-TEST-001"
    )
    assert result["workflow_status"] == "proposal_saved"

    ledger = db.inserts["research_ledger"][0]
    assert ledger["approval_status"] == "pending"
    assert (
        ledger["proposal"]["parent_experiment_id"]
        == "EXP-TEST-001"
    )


@pytest.mark.parametrize(
    "workflow_result,expected_status",
    [
        (
            {
                "status": "needs_clarification",
                "assistant_message": "Which date range should we use?",
                "usage": {"provider": "test"},
            },
            "needs_clarification",
        ),
        (
            {
                "status": "validation_failed",
                "assistant_message": "Validation failed.",
                "validation_errors": ["Unsupported feature."],
                "usage": {"provider": "test"},
            },
            "validation_failed",
        ),
    ],
)
def test_unsuccessful_design_does_not_persist_proposal(
    fake_environment,
    monkeypatch,
    workflow_result,
    expected_status,
):
    db = fake_environment

    monkeypatch.setattr(
        conversation,
        "_call_research_router",
        lambda *args: (
            routed_proposal("new_research"),
            {"provider": "test", "total_tokens": 10},
        ),
    )

    monkeypatch.setattr(
        conversation,
        "run_initial_research_design",
        lambda **kwargs: workflow_result,
    )

    result = call_chat()

    assert result["workflow_status"] == expected_status
    assert result["agent_run_id"] is None
    assert result["ledger_id"] is None
    assert "research_ledger" not in db.inserts
    assert "agent_runs" not in db.inserts
    assert result["needs_follow_up"] is True


def test_invalid_proposal_schema_does_not_create_database_records(
    fake_environment,
):
    db = fake_environment
    workflow_result = valid_workflow_result()
    workflow_result["experiment_type"] = "unsupported_type"

    with pytest.raises(Exception):
        conversation._persist_langgraph_proposal(
            session_id=SESSION_ID,
            client_message_id=MESSAGE_ID,
            routing={
                "research_action": "new_research",
                "referenced_experiment_id": None,
            },
            workflow_result=workflow_result,
        )

    assert "research_ledger" not in db.inserts
    assert "agent_runs" not in db.inserts
    assert db.rpc_calls == []


def test_retry_with_same_id_returns_saved_assistant_response(
    fake_environment,
    monkeypatch,
):
    db = fake_environment
    seed_user_message(db)

    saved_metadata = {
        "client_message_id": MESSAGE_ID,
        "intent": "propose_experiment",
        "needs_follow_up": False,
        "follow_up_question": "",
        "research_question": "Does RSI below 30 identify reversals?",
        "hypothesis": "Oversold stocks may rebound.",
        "research_action": "new_research",
        "referenced_experiment_id": None,
        "workflow_status": "proposal_saved",
        "agent_run_id": "agent-run-existing",
        "ledger_id": "ledger-existing",
        "usage": {"router": {"total_tokens": 10}},
    }

    db.seed(
        "chat_messages",
        [{
            "session_id": str(SESSION_ID),
            "role": "assistant",
            "content": "The proposal is awaiting your approval.",
            "metadata": saved_metadata,
        }],
    )

    def unexpected_router_call(*args, **kwargs):
        pytest.fail("Router must not run for a completed retry.")

    monkeypatch.setattr(
        conversation,
        "_call_research_router",
        unexpected_router_call,
    )

    result = call_chat()

    assert result["response"] == (
        "The proposal is awaiting your approval."
    )
    assert result["workflow_status"] == "proposal_saved"
    assert result["agent_run_id"] == "agent-run-existing"
    assert result["ledger_id"] == "ledger-existing"
    assert "research_ledger" not in db.inserts
    assert "agent_runs" not in db.inserts

    assistant_messages = [
        row
        for row in db.tables["chat_messages"]
        if row["role"] == "assistant"
    ]
    assert len(assistant_messages) == 1


def test_reusing_message_id_with_different_content_returns_409(
    fake_environment,
    monkeypatch,
):
    db = fake_environment
    seed_user_message(
        db,
        client_message_id=MESSAGE_ID,
        content="Original message",
    )

    def unexpected_router_call(*args, **kwargs):
        pytest.fail("Router must not run after an idempotency conflict.")

    monkeypatch.setattr(
        conversation,
        "_call_research_router",
        unexpected_router_call,
    )

    with pytest.raises(HTTPException) as exc_info:
        call_chat(message="A different message")

    assert exc_info.value.status_code == 409
    assert (
        exc_info.value.detail["code"]
        == "IDEMPOTENCY_KEY_REUSED"
    )
    assert "research_ledger" not in db.inserts
    assert "agent_runs" not in db.inserts


def test_existing_user_message_without_assistant_response_resumes(
    fake_environment,
    monkeypatch,
):
    db = fake_environment
    seed_user_message(db)

    router_calls = []

    def fake_router(*args):
        router_calls.append(args)
        return (
            routed_non_proposal(),
            {"provider": "test", "total_tokens": 10},
        )

    monkeypatch.setattr(
        conversation,
        "_call_research_router",
        fake_router,
    )

    result = call_chat()

    assert len(router_calls) == 1
    assert result["response"] == (
        "Here is a general research explanation."
    )

    user_messages = [
        row
        for row in db.tables["chat_messages"]
        if row["role"] == "user"
    ]
    assistant_messages = [
        row
        for row in db.tables["chat_messages"]
        if row["role"] == "assistant"
    ]

    assert len(user_messages) == 1
    assert len(assistant_messages) == 1
    assert (
        assistant_messages[0]["metadata"]["client_message_id"]
        == MESSAGE_ID
    )
    assert "research_ledger" not in db.inserts
    assert "agent_runs" not in db.inserts


def test_new_message_id_runs_normal_workflow(
    fake_environment,
    monkeypatch,
):
    db = fake_environment
    router_calls = []

    def fake_router(*args):
        router_calls.append(args)
        return (
            routed_non_proposal(),
            {"provider": "test", "total_tokens": 10},
        )

    monkeypatch.setattr(
        conversation,
        "_call_research_router",
        fake_router,
    )

    result = call_chat(client_message_id="new-message-002")

    assert len(router_calls) == 1
    assert result["response"] == (
        "Here is a general research explanation."
    )

    user_messages = [
        row
        for row in db.tables["chat_messages"]
        if row["role"] == "user"
    ]
    assistant_messages = [
        row
        for row in db.tables["chat_messages"]
        if row["role"] == "assistant"
    ]

    assert len(user_messages) == 1
    assert len(assistant_messages) == 1
    assert (
        user_messages[0]["metadata"]["client_message_id"]
        == "new-message-002"
    )
    assert (
        assistant_messages[0]["metadata"]["client_message_id"]
        == "new-message-002"
    )


def test_rpc_failure_does_not_create_partial_proposal(
    fake_environment,
):
    db = fake_environment
    db.rpc_error = RuntimeError(
        "Simulated database transaction failure"
    )

    workflow_result = valid_workflow_result()

    with pytest.raises(RuntimeError):
        conversation._persist_langgraph_proposal(
            session_id=SESSION_ID,
            client_message_id=MESSAGE_ID,
            routing={
                "research_action": "new_research",
                "referenced_experiment_id": None,
            },
            workflow_result=workflow_result,
        )

    assert len(db.rpc_calls) == 1
    assert (
        db.rpc_calls[0]["function_name"]
        == "persist_langgraph_proposal_idempotent"
    )
    assert "agent_runs" not in db.inserts
    assert "research_ledger" not in db.inserts


def test_proposal_rpc_reuses_existing_proposal_for_same_message_id(
    fake_environment,
):
    db = fake_environment
    workflow_result = valid_workflow_result()
    routing = {
        "research_action": "new_research",
        "referenced_experiment_id": None,
    }

    first = conversation._persist_langgraph_proposal(
        session_id=SESSION_ID,
        client_message_id="same-request-001",
        routing=routing,
        workflow_result=workflow_result,
    )

    second = conversation._persist_langgraph_proposal(
        session_id=SESSION_ID,
        client_message_id="same-request-001",
        routing=routing,
        workflow_result=workflow_result,
    )

    assert first["agent_run_id"] == second["agent_run_id"]
    assert first["ledger_id"] == second["ledger_id"]

    assert len(db.tables["agent_runs"]) == 1
    assert len(db.tables["research_ledger"]) == 1
    assert len(db.rpc_calls) == 2
