from __future__ import annotations

# -*- coding: utf-8 -*-
"""
Created on Mon Oct  5 13:24:06 2026

@author: mohak
"""

# -*- coding: utf-8 -*-
"""
Research Agent 2 provider abstraction.

Supported providers:
- Ollama
- OpenAI
- Gemini

The LLM generates only a semantic proposal.
Python deterministically constructs the ResearchRequest.
The deterministic guardrails remain responsible for validation.
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

from api.research_agent.prompts import AGENT_2_SYSTEM_PROMPT

load_dotenv()

# ============================================================
# CONFIGURATION
# ============================================================

DEFAULT_PROVIDER = "ollama"

DEFAULT_OLLAMA_MODEL = "qwen2.5:3b"

DEFAULT_OLLAMA_URL = (
    "http://127.0.0.1:11434/api/chat"
)

DEFAULT_OPENAI_MODEL = "gpt-6-luna"

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"


def get_agent_provider() -> str:
    return os.getenv(
        "RESEARCH_AGENT_PROVIDER",
        DEFAULT_PROVIDER,
    ).strip().lower()


def get_agent_model() -> str:
    provider = get_agent_provider()

    defaults = {
        "ollama": DEFAULT_OLLAMA_MODEL,
        "openai": DEFAULT_OPENAI_MODEL,
        "gemini": DEFAULT_GEMINI_MODEL,
    }

    if provider not in defaults:
        raise ValueError(
            "Unsupported RESEARCH_AGENT_PROVIDER: "
            f"{provider}"
        )

    return os.getenv(
        "RESEARCH_AGENT_MODEL",
        defaults[provider],
    ).strip()


# ============================================================
# PROVIDER CLIENTS
# ============================================================

def get_openai_client():
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured."
        )

    return OpenAI(api_key=api_key)


def get_gemini_client():
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured."
        )

    return genai.Client(api_key=api_key)


# ============================================================
# CONTEXT PREPARATION AND COST GUARDS
# ============================================================

# The previous compactor limited each nested dictionary/list separately.
# That allowed multiplicative growth (for example 40 keys x 8 items x
# several nested levels), producing a 123k-character prompt. The new
# approach is allowlist-based for the ResearchRequest and extracts only
# scalar evidence metrics from result objects.
DEFAULT_MAX_AGENT2_INPUT_CHARS = 24000
DEFAULT_MAX_AGENT2_HISTORY_ITEMS = 3
DEFAULT_MAX_AGENT2_USER_PROMPT_CHARS = 16000

_OMIT_CONTEXT_KEYS = {
    "trades", "trade_log", "trade_logs", "equity_curve",
    "daily_returns", "returns_series", "price_series", "prices",
    "ohlcv", "candles", "bars", "raw_data", "raw_prices",
    "raw_returns", "observations", "records", "transactions",
    "signals", "per_trade", "trade_details", "all_trades",
    "dataframe", "df", "daily_data", "historical_data",
}

_REQUEST_FIELDS = (
    "development_start", "development_end",
    "validation_start", "validation_end",
    "holdout_start", "holdout_end",
    "universe", "features", "entry_conditions",
    "evaluation_horizons", "signal_timing", "outcome_definition",
)


def _agent2_limit(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default))
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _small_json_value(value: Any, *, depth: int = 0) -> Any:
    """Bound small configuration objects; never use on full result payloads."""
    if depth >= 4:
        return "[nested detail omitted]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        limit = _agent2_limit("AGENT2_MAX_STRING_CHARS", 240)
        return value if len(value) <= limit else value[:limit] + "...[cut]"
    if hasattr(value, "model_dump"):
        try:
            value = value.model_dump(mode="json")
        except Exception:
            return "[unsupported value omitted]"
    if isinstance(value, dict):
        result = {}
        for key, child in list(value.items())[:16]:
            key_text = str(key)
            if key_text.lower() in _OMIT_CONTEXT_KEYS:
                continue
            result[key_text] = _small_json_value(child, depth=depth + 1)
        return result
    if isinstance(value, (list, tuple, set)):
        return [
            _small_json_value(item, depth=depth + 1)
            for item in list(value)[:12]
        ]
    return str(value)[:160]


def _compact_research_request(base_request: Any) -> dict[str, Any]:
    if hasattr(base_request, "model_dump"):
        raw = base_request.model_dump(mode="json")
    elif isinstance(base_request, dict):
        raw = base_request
    else:
        return {}

    # Only fields that define the experiment are relevant to Agent 2.
    return {
        key: _small_json_value(raw.get(key))
        for key in _REQUEST_FIELDS
        if key in raw and raw.get(key) is not None
    }


def _compact_stage_evidence(stage: Any, *, max_metrics: int = 24) -> dict[str, Any]:
    """Extract a bounded set of scalar metrics and short diagnostic text."""
    if not isinstance(stage, dict):
        if hasattr(stage, "model_dump"):
            try:
                stage = stage.model_dump(mode="json")
            except Exception:
                return {}
        else:
            return {}

    metrics: dict[str, Any] = {}
    diagnostic_text: dict[str, str] = {}
    preferred_terms = (
        "metric", "summary", "stat", "performance", "return", "win",
        "signal", "sample", "count", "p_value", "pvalue", "sharpe",
        "drawdown", "confidence", "interval", "warning", "status",
        "interpret", "conclusion", "robust", "mae", "mse", "rank",
    )
    text_terms = ("warning", "status", "interpret", "conclusion", "message", "note")

    def walk(obj: Any, path: str = "", depth: int = 0) -> None:
        if depth > 4 or len(metrics) + len(diagnostic_text) >= max_metrics:
            return
        if hasattr(obj, "model_dump"):
            try:
                obj = obj.model_dump(mode="json")
            except Exception:
                return
        if not isinstance(obj, dict):
            return

        # Prioritize summary/statistics-like branches before other branches.
        entries = list(obj.items())
        entries.sort(
            key=lambda pair: 0 if any(term in str(pair[0]).lower() for term in preferred_terms) else 1
        )
        for key, value in entries:
            if len(metrics) + len(diagnostic_text) >= max_metrics:
                break
            key_text = str(key)
            low_key = key_text.lower()
            if low_key in _OMIT_CONTEXT_KEYS:
                continue
            full_key = f"{path}.{key_text}" if path else key_text
            if isinstance(value, (bool, int, float)) or value is None:
                if any(term in low_key for term in preferred_terms) or isinstance(value, bool):
                    metrics[full_key] = value
            elif isinstance(value, str):
                if any(term in low_key for term in text_terms):
                    diagnostic_text[full_key] = value[:220]
            elif isinstance(value, dict):
                walk(value, full_key, depth + 1)
            # Lists are deliberately omitted: they commonly contain trades,
            # per-symbol rows, dates or time-series and caused prompt blow-up.

    walk(stage)
    result: dict[str, Any] = {}
    if metrics:
        result["metrics"] = metrics
    if diagnostic_text:
        result["diagnostics"] = diagnostic_text
    return result


def _compact_latest_result(latest_result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(latest_result, dict) or not latest_result:
        return {}

    compact: dict[str, Any] = {}
    for stage_name in ("development", "validation", "final_holdout"):
        stage = latest_result.get(stage_name)
        if stage is not None:
            stage_summary = _compact_stage_evidence(stage)
            if stage_summary:
                compact[stage_name] = stage_summary

    # Include only a small subset of the config for context, not a second
    # full copy of the ResearchRequest.
    config = latest_result.get("research_config")
    if isinstance(config, dict):
        config_summary = {
            key: _small_json_value(config.get(key))
            for key in (
                "universe", "evaluation_horizons", "signal_timing",
                "outcome_definition", "development_start", "development_end",
                "validation_start", "validation_end", "holdout_start", "holdout_end",
            )
            if key in config and config.get(key) is not None
        }
        if config_summary:
            compact["research_config_summary"] = config_summary
    return compact


def _compact_history(history: list[Any]) -> list[dict[str, Any]]:
    if not history:
        return []
    max_history = _agent2_limit(
        "AGENT2_MAX_HISTORY_ITEMS",
        DEFAULT_MAX_AGENT2_HISTORY_ITEMS,
    )
    compact_history = []
    for item in list(history)[-max_history:]:
        if hasattr(item, "model_dump"):
            try:
                item_dict = item.model_dump(mode="json")
            except Exception:
                continue
        elif isinstance(item, dict):
            item_dict = item
        else:
            continue

        entry = {}
        for key in (
            "experiment_id", "parent_experiment_id", "status",
            "research_question", "hypothesis", "experiment_type",
        ):
            value = item_dict.get(key)
            if value is not None:
                entry[key] = _small_json_value(value)

        # Keep only scalar metrics from historical results; never embed the
        # previous full ResearchRequest or raw result object.
        result = item_dict.get("research_result")
        if isinstance(result, dict):
            stage = result.get("development") or result.get("summary") or result
            summary = _compact_stage_evidence(stage, max_metrics=10)
            if summary:
                entry["result_summary"] = summary
        compact_history.append(entry)
    return compact_history


def _build_user_prompt(request: Agent2Request) -> str:
    """Build a small, non-duplicated context payload for Agent 2."""
    payload = {
        "CURRENT_RESEARCH_QUESTION": str(request.research_question or "")[:700],
        "CURRENT_HYPOTHESIS": str(request.hypothesis or "")[:700],
        "CURRENT_RESEARCH_REQUEST": _compact_research_request(
            request.base_research_request
        ),
        "LATEST_RESEARCH_EVIDENCE": _compact_latest_result(
            request.latest_result
        ),
        "EXPERIMENT_HISTORY": _compact_history(
            request.experiment_history
        ),
    }

    prompt_prefix = (
        "Use only the supplied research context. The current ResearchRequest "
        "is authoritative. Propose exactly ONE controlled next experiment. "
        "Do not invent features, parameters, returns or statistical findings. "
        "Do not use final-holdout evidence to generate an iterative hypothesis. "
        "Make one isolated change. The Python research engine and guardrails "
        "will validate the proposal.\n\nRESEARCH CONTEXT (JSON):\n"
    )
    prompt = prompt_prefix + json.dumps(
        payload,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )

    max_chars = _agent2_limit(
        "AGENT2_MAX_USER_PROMPT_CHARS",
        DEFAULT_MAX_AGENT2_USER_PROMPT_CHARS,
    )
    if len(prompt) > max_chars:
        # Degrade context safely in a known order: remove history first,
        # then reduce evidence metrics. Never send an oversized prompt.
        payload["EXPERIMENT_HISTORY"] = []
        prompt = prompt_prefix + json.dumps(payload, separators=(",", ":"), ensure_ascii=True, default=str)

    if len(prompt) > max_chars:
        payload["LATEST_RESEARCH_EVIDENCE"] = {
            "note": "Evidence omitted because its serialized size exceeded the local prompt budget."
        }
        prompt = prompt_prefix + json.dumps(payload, separators=(",", ":"), ensure_ascii=True, default=str)

    if len(prompt) > max_chars:
        raise ValueError(
            "Agent 2 core research configuration exceeds the local prompt budget "
            f"({len(prompt):,} characters; limit {max_chars:,}). "
            "No LLM request was sent. Reduce the research question/configuration."
        )

    return prompt


def _check_provider_input_budget(system_prompt: str, user_prompt: str) -> None:
    """Hard preflight character budget before any paid provider request."""
    max_total_chars = _agent2_limit(
        "AGENT2_MAX_TOTAL_INPUT_CHARS",
        DEFAULT_MAX_AGENT2_INPUT_CHARS,
    )
    total_chars = len(system_prompt) + len(user_prompt)
    if total_chars > max_total_chars:
        estimated_tokens = (total_chars + 2) // 3
        raise ValueError(
            "Agent 2 input budget exceeded before provider call: "
            f"{total_chars:,} characters (roughly {estimated_tokens:,} tokens); "
            f"configured character limit is {max_total_chars:,}. "
            "No LLM request was sent. Increase the limit only after reviewing prompt size."
        )


# ============================================================
# DETERMINISTIC RESEARCH REQUEST CONSTRUCTION
# ============================================================

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

    target_feature = semantic.target_feature

    if not target_feature:
        raise ValueError(
            "Threshold sensitivity requires target_feature."
        )

    target_period = semantic.target_period

    matching_conditions = []

    for condition in conditions:

        if not isinstance(condition, dict):
            continue

        left = condition.get("left", {})

        if not isinstance(left, dict):
            continue

        left_feature = left.get("feature")

        if left_feature != target_feature:
            continue

        parameters = left.get("parameters", {})

        if not isinstance(parameters, dict):
            parameters = {}

        if target_period is not None:

            existing_period = parameters.get("period")

            if existing_period != target_period:
                continue

        right = condition.get("right", {})

        if not isinstance(right, dict):
            continue

        right_value = right.get("value")

        if not isinstance(right_value, (int, float)):
            continue

        matching_conditions.append(condition)

    if not matching_conditions:

        period_text = (
            f" with period {target_period}"
            if target_period is not None
            else ""
        )

        raise ValueError(
            "Could not find an existing numeric entry "
            "condition matching target feature "
            f"'{target_feature}'{period_text}."
        )

    if len(matching_conditions) > 1:

        period_text = (
            f" with period {target_period}"
            if target_period is not None
            else ""
        )

        raise ValueError(
            "Threshold target is ambiguous. Multiple "
            "entry conditions match "
            f"'{target_feature}'{period_text}."
        )

    target_condition = matching_conditions[0]

    existing_operator = target_condition.get("operator")

    if semantic.threshold_operator != existing_operator:
        raise ValueError(
            "Threshold sensitivity cannot change "
            "the existing comparison operator. "
            f"Existing operator: '{existing_operator}', "
            f"proposed operator: '{semantic.threshold_operator}'."
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

    if not isinstance(outcome_definition, dict):
        raise ValueError(
            "Base request has no valid outcome_definition."
        )

    outcome_definition["horizons"] = horizons


def _apply_confirmation_feature(
    proposed: dict[str, Any],
    semantic: Agent2SemanticProposal,
) -> None:

    feature_name = semantic.confirmation_feature

    if not feature_name:
        raise ValueError(
            "Confirmation feature is required."
        )

    feature_parameters = {}

    if semantic.confirmation_period:
        feature_parameters["period"] = (
            semantic.confirmation_period
        )

    features = proposed.setdefault("features", [])

    feature_already_exists = any(
        feature.get("type") == feature_name
        for feature in features
        if isinstance(feature, dict)
    )

    if not feature_already_exists:
        features.append(
            {
                "type": feature_name,
                "parameters": feature_parameters,
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

    experiment_type = semantic.experiment_type

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

    return ResearchRequest.model_validate(proposed)


# ============================================================
# COMMON PROPOSAL CONSTRUCTION
# ============================================================

def _build_agent2_response(
    request: Agent2Request,
    semantic: Agent2SemanticProposal,
    model: str,
    usage: dict[str, Any] | None = None,
) -> Agent2Response:

    try:

        research_request = _build_research_request(
            request.base_research_request,
            semantic,
        )

    except Exception as exc:

        raise RuntimeError(
            "Agent 2 semantic proposal could not "
            "be converted into a valid ResearchRequest: "
            f"{exc}"
        ) from exc

    proposal = Agent2Proposal(
        research_question=semantic.research_question,
        hypothesis=semantic.hypothesis,
        rationale=semantic.rationale,
        expected_learning=semantic.expected_learning,
        experiment_type=semantic.experiment_type,
        confidence=semantic.confidence,
        research_request=research_request,
    )

    return Agent2Response(
        proposal=proposal,
        model=model,
        usage=usage or {},
    )


# ============================================================
# OLLAMA PROVIDER
# ============================================================

def _call_ollama(
    request: Agent2Request,
) -> Agent2Response:

    model = get_agent_model()

    user_prompt = _build_user_prompt(request)

    system_prompt = AGENT_2_SYSTEM_PROMPT + """

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
"""
    _check_provider_input_budget(system_prompt, user_prompt)

    schema = Agent2SemanticProposal.model_json_schema()

    payload = {
        "model": model,

        "messages": [
            {
                "role": "system",
                "content": system_prompt,
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
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:

        with urlopen(
            http_request,
            timeout=300,
        ) as response:

            raw_response = (
                response.read().decode("utf-8")
            )

    except HTTPError as exc:

        error_body = exc.read().decode(
            "utf-8",
            errors="replace",
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

        response_data = json.loads(raw_response)

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

        semantic = Agent2SemanticProposal.model_validate_json(
            content
        )

    except Exception as exc:

        raise RuntimeError(
            "Ollama returned invalid semantic "
            f"Agent 2 output: {exc}"
        ) from exc

    usage = {
        "prompt_tokens":
            response_data.get("prompt_eval_count"),

        "completion_tokens":
            response_data.get("eval_count"),

        "total_duration_ns":
            response_data.get("total_duration"),

        "load_duration_ns":
            response_data.get("load_duration"),

        "provider": "ollama",
    }

    return _build_agent2_response(
        request=request,
        semantic=semantic,
        model=model,
        usage=usage,
    )


# ============================================================
# OPENAI PROVIDER
# ============================================================

def _call_openai(
    request: Agent2Request,
) -> Agent2Response:

    client = get_openai_client()

    model = get_agent_model()

    user_prompt = _build_user_prompt(request)

    system_prompt = AGENT_2_SYSTEM_PROMPT + """

IMPORTANT OUTPUT RULE:

Return ONLY the semantic Agent2SemanticProposal.
Do NOT construct a ResearchRequest.
The application will construct it deterministically.
"""
    _check_provider_input_budget(system_prompt, user_prompt)

    response = client.responses.parse(
        model=model,

        input=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],

        text_format=Agent2SemanticProposal,

        max_output_tokens=1000,
    )

    semantic = response.output_parsed

    if semantic is None:
        raise RuntimeError(
            "OpenAI returned no structured Agent 2 proposal."
        )

    usage = {}

    if response.usage is not None:

        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.total_tokens,
            "provider": "openai",
        }

    return _build_agent2_response(
        request=request,
        semantic=semantic,
        model=model,
        usage=usage,
    )


# ============================================================
# GEMINI PROVIDER
# ============================================================

def _call_gemini(
    request: Agent2Request,
) -> Agent2Response:

    from google.genai import types

    client = get_gemini_client()

    model = get_agent_model()

    user_prompt = _build_user_prompt(request)

    system_prompt = (
        AGENT_2_SYSTEM_PROMPT
        + """

IMPORTANT OUTPUT RULE:

Return ONLY the semantic Agent2SemanticProposal.

Do NOT construct a ResearchRequest.
The application will construct it deterministically.

Never return explanations outside the structured output.
"""
    )

    _check_provider_input_budget(system_prompt, user_prompt)

    try:

        response = client.models.generate_content(
            model=model,

            contents=user_prompt,

            config=types.GenerateContentConfig(
                system_instruction=system_prompt,

                response_mime_type="application/json",

                response_schema=Agent2SemanticProposal,

                temperature=0.2,

                max_output_tokens=600,

                http_options=types.HttpOptions(
                    timeout=60000,
                ),
            ),
        )

    except Exception as exc:

        raise RuntimeError(
            "Gemini API request failed: "
            f"{type(exc).__name__}: {exc}"
        ) from exc

    semantic = getattr(
        response,
        "parsed",
        None,
    )

    if semantic is None:

        response_text = getattr(
            response,
            "text",
            None,
        )

        if not response_text:
            raise RuntimeError(
                "Gemini returned an empty Agent 2 response."
            )

        try:

            semantic = (
                Agent2SemanticProposal.model_validate_json(
                    response_text
                )
            )

        except Exception as exc:

            raise RuntimeError(
                "Gemini returned invalid semantic "
                f"Agent 2 output: {exc}"
            ) from exc

    usage = {}

    metadata = getattr(
        response,
        "usage_metadata",
        None,
    )

    if metadata is not None:

        usage = {
            "input_tokens":
                getattr(
                    metadata,
                    "prompt_token_count",
                    None,
                ),

            "output_tokens":
                getattr(
                    metadata,
                    "candidates_token_count",
                    None,
                ),

            "total_tokens":
                getattr(
                    metadata,
                    "total_token_count",
                    None,
                ),

            "provider": "gemini",
        }

    return _build_agent2_response(
        request=request,
        semantic=semantic,
        model=model,
        usage=usage,
    )


# ============================================================
# PUBLIC ENTRY POINT
# ============================================================

def propose_next_experiment(
    request: Agent2Request,
) -> Agent2Response:

    provider = get_agent_provider()

    if provider == "ollama":
        return _call_ollama(request)

    if provider == "openai":
        return _call_openai(request)

    if provider == "gemini":
        return _call_gemini(request)

    raise ValueError(
        "Unsupported Agent 2 provider: "
        f"{provider}"
    )