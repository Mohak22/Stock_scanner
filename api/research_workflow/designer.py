
from __future__ import annotations

# -*- coding: utf-8 -*-
"""
Created on Mon Nov 23 17:35:37 2026

@author: mohak
"""

import json
import os
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from api.research.features import get_feature_registry
from api.research.models import ResearchRequest


ExperimentType = Literal[
    "threshold_sensitivity",
    "confirmation_variable",
    "delivery_confirmation",
    "market_regime",
    "horizon",
    "robustness",
    "feature_interaction",
]


class ResearchDesignerOutput(BaseModel):
    status: Literal["needs_clarification", "proposal"]
    assistant_message: str = Field(min_length=1)

    research_question: str = ""
    hypothesis: str = ""
    rationale: str = ""
    expected_learning: str = ""

    experiment_type: ExperimentType | None = None
    confidence: Literal["low", "medium", "high"] = "medium"

    research_request: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_output(self):
        if self.status == "proposal":
            if self.research_request is None:
                raise ValueError(
                    "A proposal must include research_request."
                )

            required_fields = {
                "research_question": self.research_question,
                "hypothesis": self.hypothesis,
                "rationale": self.rationale,
                "expected_learning": self.expected_learning,
                "experiment_type": self.experiment_type,
            }

            missing = [
                name
                for name, value in required_fields.items()
                if value is None or not str(value).strip()
            ]

            if missing:
                raise ValueError(
                    "A proposal is missing required fields: "
                    + ", ".join(missing)
                )

        if (
            self.status == "needs_clarification"
            and self.research_request is not None
        ):
            raise ValueError(
                "A clarification response cannot contain a proposal."
            )

        return self


SHARED_DESIGNER_RULES = """
You are the Research Experiment Designer for Stock Scanner.

You design historical research experiments. You are not a trading agent.

GENERAL RULES

1. Use ONLY features in supported_features.
2. Follow research_request_schema exactly.
3. Never invent fields, feature IDs, parameters or operators.
4. Never generate Python code or arbitrary SQL.
5. Never invent market data, results or statistics.
6. Never claim approval or execution.
7. The deterministic Python research engine owns calculations.
8. Never bypass validation or human approval.
9. Ask one focused clarification question at a time.
10. Do not silently invent dates, symbols, universe or horizons.
11. Do not invent performance results or claim expected profitability.
12. Do not add complexity merely to make an experiment look advanced.

SUPPORTED EXPERIMENT TYPES

Choose exactly one:
- threshold_sensitivity
- confirmation_variable
- delivery_confirmation
- market_regime
- horizon
- robustness
- feature_interaction

Choose the type that best describes the actual research question.
Do not force an experiment into a type when the intended design
does not fit. Ask for clarification instead.

FEATURE RULES

- Use only the supplied feature registry.
- RSI below 30 may use feature "rsi", parameter {"period": 14},
  operator "<", value 30, if supported by the schema.
- Volume greater than twice average volume may use "volume" and
  "average_volume" if the feature definitions support the comparison.
- Do not assume whether a rolling average includes the current day.
  Flag this if it materially affects the hypothesis.

TEMPORAL CONVENTION

The current engine uses:
- observation: signal_date_close
- entry: same_signal_date_close_proxy
- price basis: CLOSE

Do not describe this as a guaranteed executable fill.

OUTPUT

Return valid JSON only:

{
  "status": "needs_clarification" or "proposal",
  "assistant_message": "Explanation for the user",
  "research_question": "Research question",
  "hypothesis": "Measurable hypothesis",
  "rationale": "Why the hypothesis is worth testing",
  "expected_learning": "What the experiment will help us learn",
  "experiment_type": "one supported experiment type",
  "confidence": "low, medium or high",
  "research_request": null or a complete ResearchRequest object
}

For clarification:
- research_request must be null.
- Ask one focused question.
- Do not pretend a complete proposal exists.

For proposal:
- research_request must be a complete valid candidate.
- rationale and expected_learning must be specific and honest.
- experiment_type must be one of the supported values.
- confidence reflects confidence in the research design,
  not confidence that the strategy will make money.
- Explain assumptions.
- Never say the proposal has been approved or executed.
"""


INITIAL_DESIGNER_PROMPT = """
DESIGN MODE: INITIAL EXPERIMENT

The user wants to investigate a new, independent research hypothesis.

Your job:
- Translate the user's idea into a measurable hypothesis.
- Identify the outcome and comparison needed to test it.
- Ask for missing essential information.
- Design a new experiment from the user's stated requirements.
- Do not use a previous experiment as a baseline unless the user
  explicitly asks to build on one.

Essential information includes:
- Measurable hypothesis.
- Development start and end dates.
- Supported universe.
- At least one supported feature.
- At least one valid entry condition.
- Evaluation horizons.

Do not invent missing values. Ask focused questions.
"""


FOLLOW_UP_DESIGNER_PROMPT = """
DESIGN MODE: FOLLOW-UP EXPERIMENT

The user explicitly wants to improve or modify a previous experiment.

The input contains:
- prior_research_request: the previous validated configuration.
- evidence_summary: compact factual evidence from the previous run.
- previous_experiment_id: the saved experiment identifier.

Rules:
- Treat prior_research_request as the baseline configuration.
- Treat evidence_summary as the factual result of the previous run.
- Never invent, exaggerate or reinterpret missing findings as facts.
- Preserve dates, universe, timing and evaluation horizons unless
  the user explicitly asks to change them or there is a clear reason.
- Change only what is necessary to test the user's proposed improvement.
- Explain exactly what changes and why.
- Do not add features or conditions just to make the experiment
  look more sophisticated.
- A follow-up must be a complete ResearchRequest, not a partial patch.
- If the user's requested change is unclear, ask one focused question.
- If the previous evidence does not justify the proposed change,
  explain that limitation.
- Set the experiment type to the best-fitting supported category.
"""


def build_designer_system_prompt(
    design_mode: Literal["initial", "follow_up"],
) -> str:
    if design_mode == "initial":
        mode_prompt = INITIAL_DESIGNER_PROMPT
    elif design_mode == "follow_up":
        mode_prompt = FOLLOW_UP_DESIGNER_PROMPT
    else:
        raise ValueError(f"Unsupported design mode: {design_mode}")

    return SHARED_DESIGNER_RULES + "\n\n" + mode_prompt


def design_experiment(
    *,
    user_message: str,
    conversation_history: list[dict[str, str]] | None = None,
    design_mode: Literal["initial", "follow_up"] = "initial",
    prior_research_request: dict[str, Any] | None = None,
    evidence_summary: dict[str, Any] | None = None,
    previous_experiment_id: str | None = None,
) -> tuple[ResearchDesignerOutput, dict[str, Any]]:

    if design_mode == "follow_up":
        if not prior_research_request or not evidence_summary:
            raise ValueError(
                "Follow-up design requires the previous request "
                "and its evidence summary."
            )

    if design_mode == "initial" and any([
        prior_research_request,
        evidence_summary,
        previous_experiment_id,
    ]):
        raise ValueError(
            "Initial design must not receive previous experiment context."
        )

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    from google import genai
    from google.genai import types

    model = os.getenv(
        "RESEARCH_DESIGNER_MODEL",
        os.getenv("RESEARCH_ROUTER_MODEL", "gemini-3.5-flash-lite"),
    )

    context = {
        "conversation_history": conversation_history or [],
        "latest_user_message": user_message,
        "supported_features": get_feature_registry(),
        "research_request_schema": ResearchRequest.model_json_schema(),
        "supported_experiment_types": [
            "threshold_sensitivity",
            "confirmation_variable",
            "delivery_confirmation",
            "market_regime",
            "horizon",
            "robustness",
            "feature_interaction",
        ],
    }

    if design_mode == "follow_up":
        context.update({
            "previous_experiment_id": previous_experiment_id,
            "prior_research_request": prior_research_request,
            "evidence_summary": evidence_summary,
        })

    system_prompt = build_designer_system_prompt(design_mode)

    prompt = (
        system_prompt
        + "\n\nINPUT CONTEXT:\n"
        + json.dumps(context, ensure_ascii=False, default=str)
    )

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.15,
            max_output_tokens=2600,
            response_mime_type="application/json",
        ),
    )

    raw_text = getattr(response, "text", None)

    if not raw_text:
        raise RuntimeError(
            "Research Designer returned an empty response."
        )

    result = ResearchDesignerOutput.model_validate_json(raw_text)

    usage_metadata = getattr(response, "usage_metadata", None)

    usage = {
        "provider": "gemini",
        "model": model,
        "input_tokens": getattr(
            usage_metadata, "prompt_token_count", 0
        ) or 0,
        "output_tokens": getattr(
            usage_metadata, "candidates_token_count", 0
        ) or 0,
        "total_tokens": getattr(
            usage_metadata, "total_token_count", 0
        ) or 0,
    }

    return result, usage


def design_initial_experiment(**kwargs):
    return design_experiment(
        design_mode="initial",
        **kwargs,
    )


def design_follow_up_experiment(**kwargs):
    return design_experiment(
        design_mode="follow_up",
        **kwargs,
    )
