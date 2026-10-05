
from __future__ import annotations

# -*- coding: utf-8 -*-
"""
Created on Mon Oct  5 13:24:06 2026

@author: mohak
"""

import copy
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request as URLRequest
from urllib.request import urlopen

from dotenv import load_dotenv

from api.research_agent.models import (
    Agent2Proposal,
    Agent2Request,
    Agent2Response,
    Agent2SemanticProposal,
)
from api.research_agent.prompts import (
    AGENT_2_SYSTEM_PROMPT,
    build_agent_2_user_prompt,
)

load_dotenv()

DEFAULT_PROVIDER = "ollama"
DEFAULT_OLLAMA_MODEL = "qwen2.5:3b"
DEFAULT_OLLAMA_URL = (
    "http://127.0.0.1:11434/api/chat"
)
DEFAULT_OPENAI_MODEL = "gpt-6-luna"


def get_agent_provider() -> str:
    return os.getenv(
        "RESEARCH_AGENT_PROVIDER",
        DEFAULT_PROVIDER,
    ).strip().lower()


def get_agent_model() -> str:
    provider = get_agent_provider()

    if provider == "ollama":
        return os.getenv(
            "RESEARCH_AGENT_MODEL",
            DEFAULT_OLLAMA_MODEL,
        ).strip()

    if provider == "openai":
        return os.getenv(
            "RESEARCH_AGENT_MODEL",
            DEFAULT_OPENAI_MODEL,
        ).strip()

    raise ValueError(
        "Unsupported RESEARCH_AGENT_PROVIDER: "
        f"{provider}"
    )


def get_openai_client():
    from openai import OpenAI

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured."
        )

    return OpenAI(api_key=api_key)


def _compact_latest_result(
    latest_result: dict[str, Any],
) -> dict[str, Any]:

    if not latest_result:
        return {}

    compact = {}

    for key in (
        "research_config",
        "development",
        "validation",
        "final_holdout",
    ):
        if key in latest_result:
            compact[key] = latest_result[key]

    return compact


def _compact_history(
    history: list[Any],
) -> list[dict[str, Any]]:

    compact_history = []

    for item in history:

        if hasattr(item, "model_dump"):
            item_dict = item.model_dump(
                mode="json"
            )
        else:
            item_dict = dict(item)

        compact_history.append(
            {
                "experiment_id":
                    item_dict.get(
                        "experiment_id"
                    ),

                "parent_experiment_id":
                    item_dict.get(
                        "parent_experiment_id"
                    ),

                "status":
                    item_dict.get("status"),

                "research_question":
                    item_dict.get(
                        "research_question"
                    ),

                "hypothesis":
                    item_dict.get(
                        "hypothesis"
                    ),

                "experiment_type":
                    item_dict.get(
                        "experiment_type"
                    ),

                "research_request":
                    item_dict.get(
                        "research_request"
                    ),

                "research_result":
                    item_dict.get(
                        "research_result"
                    ),
            }
        )

    return compact_history


def _build_user_prompt(
    request: Agent2Request,
) -> str:

    return build_agent_2_user_prompt(
        research_question=
            request.research_question,

        hypothesis=
            request.hypothesis,

        base_research_request=
            request.base_research_request.model_dump(
                mode="json"
            ),

        latest_result=
            _compact_latest_result(
                request.latest_result
            ),

        experiment_history=
            _compact_history(
                request.experiment_history
            ),
    )


def _apply_threshold_sensitivity(
    proposed: dict[str, Any],
    semantic: Agent2SemanticProposal,
) -> None:

    conditions = proposed.get(
        "entry_conditions",
        [],
    )

    if not conditions:
        raise ValueError(
            "Threshold sensitivity requires "
            "at least one existing entry condition."
        )

    target_condition = None

    for condition in conditions:

        right = condition.get(
            "right",
            {}
        )

        if (
            isinstance(right, dict)
            and isinstance(
                right.get("value"),
                (int, float),
            )
        ):
            target_condition = condition
            break

    if target_condition is None:
        raise ValueError(
            "Could not find a numeric threshold "
            "in the existing entry conditions."
        )

    target_condition["operator"] = (
        semantic.threshold_operator
    )

    target_condition["right"]["value"] = (
        semantic.threshold_value
    )


def _apply_horizon_change(
    proposed: dict[str, Any],
    semantic: Agent2SemanticProposal,
) -> None:

    horizons = semantic.horizons

    if not horizons:
        raise ValueError(
            "Horizon experiment requires horizons."
        )

    horizons = sorted(set(horizons))

    proposed["evaluation_horizons"] = horizons

    outcome_definition = proposed.get(
        "outcome_definition"
    )

    if not isinstance(
        outcome_definition,
        dict,
    ):
        raise ValueError(
            "Base request has no valid "
            "outcome_definition."
        )

    outcome_definition["horizons"] = horizons


def _apply_confirmation_feature(
    proposed: dict[str, Any],
    semantic: Agent2SemanticProposal,
) -> None:

    feature_name = (
        semantic.confirmation_feature
    )

    if not feature_name:
        raise ValueError(
            "Confirmation feature is required."
        )

    feature_parameters = {}

    if semantic.confirmation_period:
        feature_parameters["period"] = (
            semantic.confirmation_period
        )

    features = proposed.setdefault(
        "features",
        [],
    )

    feature_already_exists = any(
        feature.get("type") == feature_name
        for feature in features
        if isinstance(feature, dict)
    )

    if not feature_already_exists:
        features.append(
            {
                "type": feature_name,
                "parameters":
                    feature_parameters,
            }
        )


def _build_research_request(
    base_request,
    semantic: Agent2SemanticProposal,
):
    proposed = copy.deepcopy(
        base_request.model_dump(
            mode="python"
        )
    )

    experiment_type = (
        semantic.experiment_type
    )

    if experiment_type == "threshold_sensitivity":

        _apply_threshold_sensitivity(
            proposed,
            semantic,
        )

    elif experiment_type == "horizon":

        _apply_horizon_change(
            proposed,
            semantic,
        )

    elif experiment_type in {
        "confirmation_variable",
        "delivery_confirmation",
    }:

        _apply_confirmation_feature(
            proposed,
            semantic,
        )

    elif experiment_type in {
        "market_regime",
        "robustness",
        "feature_interaction",
    }:

        pass

    else:
        raise ValueError(
            "Unsupported Agent 2 experiment type: "
            f"{experiment_type}"
        )

    from api.research.models import ResearchRequest

    return ResearchRequest.model_validate(
        proposed
    )


def _call_ollama(
    request: Agent2Request,
) -> Agent2Response:

    model = get_agent_model()

    user_prompt = _build_user_prompt(
        request
    )

    schema = (
        Agent2SemanticProposal
        .model_json_schema()
    )

    payload = {
        "model": model,

        "messages": [
            {
                "role": "system",
                "content":
                    AGENT_2_SYSTEM_PROMPT
                    + """

IMPORTANT OUTPUT RULE:

Do NOT construct a ResearchRequest.

Return ONLY the small semantic
Agent2SemanticProposal.

The application will construct the
ResearchRequest deterministically.

For threshold_sensitivity:
- provide threshold_value
- provide threshold_operator

For horizon:
- provide horizons

For confirmation_variable or
delivery_confirmation:
- provide confirmation_feature
- provide confirmation_period
  only when applicable

Never invent feature names.
Use only capabilities explicitly
described in the research context.
""",
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],

        "stream": False,

        "format": schema,

        "options": {
            "temperature": 0.2,
            "num_predict": 1000,
        },

        "keep_alive": "5m",
    }

    encoded_payload = json.dumps(
        payload
    ).encode("utf-8")

    http_request = URLRequest(
        os.getenv(
            "OLLAMA_API_URL",
            DEFAULT_OLLAMA_URL,
        ),
        data=encoded_payload,
        headers={
            "Content-Type":
                "application/json",
        },
        method="POST",
    )

    try:

        with urlopen(
            http_request,
            timeout=300,
        ) as response:

            raw_response = (
                response
                .read()
                .decode("utf-8")
            )

    except HTTPError as exc:

        error_body = (
            exc.read()
            .decode(
                "utf-8",
                errors="replace",
            )
        )

        raise RuntimeError(
            "Ollama API request failed: "
            f"HTTP {exc.code}: {error_body}"
        ) from exc

    except URLError as exc:

        raise RuntimeError(
            "Could not connect to Ollama at "
            f"{os.getenv('OLLAMA_API_URL', DEFAULT_OLLAMA_URL)}. "
            "Make sure Ollama is running."
        ) from exc

    except TimeoutError as exc:

        raise RuntimeError(
            "Ollama request timed out."
        ) from exc

    try:

        response_data = json.loads(
            raw_response
        )

    except json.JSONDecodeError as exc:

        raise RuntimeError(
            "Ollama returned invalid JSON."
        ) from exc

    content = (
        response_data
        .get("message", {})
        .get("content")
    )

    if not content:

        raise RuntimeError(
            "Ollama returned an empty Agent 2 response."
        )

    try:

        semantic = (
            Agent2SemanticProposal
            .model_validate_json(
                content
            )
        )

    except Exception as exc:

        raise RuntimeError(
            "Ollama returned invalid semantic "
            "Agent 2 output: "
            f"{exc}"
        ) from exc

    try:

        research_request = (
            _build_research_request(
                request.base_research_request,
                semantic,
            )
        )

    except Exception as exc:

        raise RuntimeError(
            "Agent 2 semantic proposal could not "
            "be converted into a valid ResearchRequest: "
            f"{exc}"
        ) from exc

    proposal = Agent2Proposal(
        research_question=
            semantic.research_question,

        hypothesis=
            semantic.hypothesis,

        rationale=
            semantic.rationale,

        expected_learning=
            semantic.expected_learning,

        experiment_type=
            semantic.experiment_type,

        confidence=
            semantic.confidence,

        research_request=
            research_request,
    )

    usage = {
        "prompt_tokens":
            response_data.get(
                "prompt_eval_count"
            ),

        "completion_tokens":
            response_data.get(
                "eval_count"
            ),

        "total_duration_ns":
            response_data.get(
                "total_duration"
            ),

        "load_duration_ns":
            response_data.get(
                "load_duration"
            ),

        "provider":
            "ollama",
    }

    return Agent2Response(
        proposal=proposal,
        model=model,
        usage=usage,
    )


def _call_openai(
    request: Agent2Request,
) -> Agent2Response:

    client = get_openai_client()

    model = get_agent_model()

    user_prompt = _build_user_prompt(
        request
    )

    response = client.responses.parse(
        model=model,

        input=[
            {
                "role": "system",
                "content":
                    AGENT_2_SYSTEM_PROMPT
                    + """

IMPORTANT OUTPUT RULE:

Return ONLY the semantic
Agent2SemanticProposal.

Do NOT construct a ResearchRequest.
The application will construct it.
""",
            },
            {
                "role": "user",
                "content":
                    user_prompt,
            },
        ],

        text_format=
            Agent2SemanticProposal,

        max_output_tokens=1000,
    )

    semantic = response.output_parsed

    if semantic is None:
        raise RuntimeError(
            "OpenAI returned no structured "
            "Agent 2 proposal."
        )

    research_request = (
        _build_research_request(
            request.base_research_request,
            semantic,
        )
    )

    proposal = Agent2Proposal(
        research_question=
            semantic.research_question,

        hypothesis=
            semantic.hypothesis,

        rationale=
            semantic.rationale,

        expected_learning=
            semantic.expected_learning,

        experiment_type=
            semantic.experiment_type,

        confidence=
            semantic.confidence,

        research_request=
            research_request,
    )

    usage = {}

    if response.usage is not None:

        usage = {
            "input_tokens":
                response.usage.input_tokens,

            "output_tokens":
                response.usage.output_tokens,

            "total_tokens":
                response.usage.total_tokens,
        }

    return Agent2Response(
        proposal=proposal,
        model=model,
        usage=usage,
    )


def propose_next_experiment(
    request: Agent2Request,
) -> Agent2Response:

    provider = get_agent_provider()

    if provider == "ollama":
        return _call_ollama(
            request
        )

    if provider == "openai":
        return _call_openai(
            request
        )

    raise ValueError(
        "Unsupported Agent 2 provider: "
        f"{provider}"
    )