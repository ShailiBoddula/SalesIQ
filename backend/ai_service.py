"""Groq-powered natural-language intent interpretation for SalesIQ.

The LLM is used ONLY to classify a user question into a known intent and
to extract structured parameters. It never generates or executes SQL.
"""

import json
import os
import re
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from groq import Groq

# Allowed intents - the LLM may only return one of these.
ALLOWED_INTENTS = (
    "total_revenue",
    "product_revenue",
    "monthly_revenue",
    "region_revenue",
    "compare_monthly_revenue",
    "unsupported",
)

# Strict YYYY-MM format used to validate comparison months.
MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

# System prompt instructing the model to return JSON only.
SYSTEM_PROMPT = """You are an intent classifier for a sales analytics assistant.

Classify the user question into exactly ONE intent and extract any parameters.
Return ONLY a JSON object with no extra text, no markdown and no explanation.

Allowed intents:
- total_revenue
- product_revenue
- monthly_revenue
- region_revenue
- compare_monthly_revenue
- unsupported

Rules:
- For compare_monthly_revenue you MUST provide month_1 and month_2 in YYYY-MM format.
- If the question cannot be answered with one of these intents, use unsupported.
- Never invent data. If months are missing, use unsupported.
- Output shape: {"intent": "...", "parameters": {"month_1": "...", "month_2": "..."}}"""

USER_PROMPT_TEMPLATE = "User question: {question}"


def _load_api_key() -> str:
    """Load the GROQ_API_KEY from the environment or a local .env file.

    Raises ValueError when the key is missing.
    """
    load_dotenv()
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is not set. Add it to your environment or .env file."
        )
    return api_key


def _build_client() -> Groq:
    """Create a Groq client using the securely loaded API key."""
    return Groq(api_key=_load_api_key())


def _validate_month(month: Any) -> Optional[str]:
    """Return the month string if it is valid YYYY-MM, otherwise None."""
    if not isinstance(month, str):
        return None
    if MONTH_PATTERN.match(month):
        return month
    return None


def _validate_intent(intent: Any) -> Optional[str]:
    """Return the intent string if it is in the allowlist, otherwise None."""
    if isinstance(intent, str) and intent in ALLOWED_INTENTS:
        return intent
    return None


def _normalize_response(raw_content: str) -> Dict[str, Any]:
    """Parse the model JSON output into a dict.

    Raises ValueError when the content is not valid JSON.
    """
    content = raw_content.strip()
    # Strip markdown code fences if the model added them anyway.
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?", "", content).strip()
        content = re.sub(r"```$", "", content).strip()
    return json.loads(content)


def interpret_question(question: str) -> Dict[str, Any]:
    """Classify a question into a SalesIQ intent using Groq.

    Returns a dict with keys:
        intent: one of the ALLOWED_INTENTS
        parameters: dict with optional month_1 / month_2 for comparisons

    Raises ValueError for missing API keys, invalid model output or
    unsupported questions that cannot be classified.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question must be a non-empty string")

    client = _build_client()

    completion = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(question=question.strip())},
        ],
        temperature=0,
        response_format={"type": "json_object"},
    )

    raw_content = completion.choices[0].message.content
    parsed = _normalize_response(raw_content)

    intent = _validate_intent(parsed.get("intent"))
    if intent is None:
        raise ValueError(f"Model returned an unknown intent: {parsed.get('intent')!r}")

    parameters = parsed.get("parameters") or {}
    if not isinstance(parameters, dict):
        parameters = {}

    if intent == "compare_monthly_revenue":
        month_1 = _validate_month(parameters.get("month_1"))
        month_2 = _validate_month(parameters.get("month_2"))
        if month_1 is None or month_2 is None:
            raise ValueError(
                "compare_monthly_revenue requires two valid YYYY-MM months, "
                f"got month_1={parameters.get('month_1')!r}, "
                f"month_2={parameters.get('month_2')!r}"
            )
        parameters = {"month_1": month_1, "month_2": month_2}
    else:
        parameters = {}

    return {"intent": intent, "parameters": parameters}
