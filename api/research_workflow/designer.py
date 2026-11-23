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


class ResearchDesignerOutput(BaseModel):
    status: Literal["needs_clarification", "proposal"]
    assistant_message: str = Field(min_length=1)

    research_question: str = ""
    hypothesis: str = ""

    research_request: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_output(self):
        if self.status == "proposal" and self.research_request is None:
            raise ValueError("A proposal must include research_request.")

        if (
            self.status == "needs_clarification"
            and self.research_request is not None
        ):
            raise ValueError(
                "A clarification response cannot contain a proposal."
            )

        return self


def design_experiment(
    *,
    user_message: str,
    conversation_history: list[dict[str, str]] | None = None,
    design_mode: Literal["initial", "follow_up"] = "initial",
    prior_research_request: dict[str, Any] | None = None,
    evidence_summary: dict[str, Any] | None = None,
    previous_experiment_id: str | None = None,
) -> tuple[ResearchDesignerOutput, dict[str, Any]]:
    """
    Design either an initial experiment or a follow-up experiment.

    This function only proposes a ResearchRequest.
    It never executes research.
    """

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    from google import genai
    from google.genai import types

    model = os.getenv(
        "RESEARCH_DESIGNER_MODEL",
        os.getenv("RESEARCH_ROUTER_MODEL", "gemini-3.5-flash-lite"),
    )

    client = genai.Client(api_key=api_key)

    context = {
        "design_mode": design_mode,
        "conversation_history": conversation_history or [],
        "latest_user_message": user_message,
        "supported_features": get_feature_registry(),
        "research_request_schema": ResearchRequest.model_json_schema(),
        "prior_research_request": prior_research_request,
        "evidence_summary": evidence_summary,
        "previous_experiment_id": previous_experiment_id,
    }

    system_prompt = """
You are the Research Experiment Designer for Stock Scanner.

Your job is to turn a user's research idea into a valid historical
experiment configuration.

You are a research-design agent, not a trading agent.

GENERAL RULES

1. Use ONLY features in supported_features.
2. Follow research_request_schema exactly.
3. Never invent fields, feature IDs, parameters or operators.
4. Never generate Python code or arbitrary SQL.
5. Never invent market data, experiment results or statistics.
6. Never claim approval or execution.
7. The deterministic Python research engine owns calculations.
8. Do not bypass validation or human approval.

DESIGN MODE

The context contains design_mode.

If design_mode is "initial":
- Design a new experiment from the user's hypothesis.
- Ask for clarification if essential information is missing.
- Do not invent dates, symbols, universe or evaluation horizons.

If design_mode is "follow_up":
- Improve the previous experiment using the supplied evidence.
- Treat prior_research_request as the baseline configuration.
- Treat evidence_summary as the factual result of the previous run.
- Do not invent or exaggerate findings.
- Preserve the previous dates, universe, timing and horizons unless
  the user explicitly asks to change them or the evidence requires
  a clearly explained change.
- Change only what is necessary for the proposed hypothesis.
- Explain exactly what changed and why.
- If evidence is insufficient to justify a change, say so and ask
  one focused clarification question.
- Do not blindly add features or conditions merely because they
  sound sophisticated.
- A follow-up proposal must be a complete ResearchRequest, not
  a partial patch.

CLARIFICATION RULES

Ask one focused question at a time when essential information is
missing or ambiguous.

Essential initial information includes:
- Measurable hypothesis.
- Development start and end dates.
- Supported universe.
- At least one supported feature.
- At least one valid entry condition.
- Evaluation horizons.

Do not silently invent missing information.

FEATURE RULES

Examples:
- RSI below 30 can use feature "rsi", parameter {"period": 14},
  operator "<", value 30.
- Volume greater than twice average volume may use "volume" and
  "average_volume" if the feature definitions support the intended
  comparison.

Do not assume whether a rolling average includes the current day.
If the hypothesis depends on this distinction, flag it.

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
  "research_request": null or a complete ResearchRequest object
}

For clarification:
- research_request must be null.
- Ask one focused question.

For proposal:
- research_request must be a complete valid candidate.
- Explain the proposed experiment and assumptions.
- For follow-up proposals, explicitly explain the changes
  relative to the previous experiment.
- Never say the proposal has been approved or executed.
"""

    prompt = (
        system_prompt
        + "\n\nINPUT CONTEXT:\n"
        + json.dumps(context, ensure_ascii=False, default=str)
    )

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.15,
            max_output_tokens=2200,
            response_mime_type="application/json",
        ),
    )

    raw_text = getattr(response, "text", None)
    if not raw_text:
        raise RuntimeError("Research Designer returned an empty response.")

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


# Backward-compatible name for any existing imports.
design_initial_experiment = design_experiment
