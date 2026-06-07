"""
Resolve ML inference payloads from natural language via LLM + Pydantic validation.

Values must be grounded in the user's text (or a prior partial payload from an
earlier turn). The LLM must not invent IDs, coordinates, or timestamps.
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config.env import load_env
from openai import OpenAI
from pydantic import BaseModel, ValidationError

REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTE_ROOT = REPO_ROOT / "ml_services" / "route_prediction"
ETA_SRC = REPO_ROOT / "ml_services" / "eta-prediction" / "src"

_env_loaded = False
_client: OpenAI | None = None

TASK_LABELS = {
    "eta": "ETA prediction",
    "next_stop": "next stop prediction",
    "route": "route sequence prediction",
}

_TEMPLATE_QUESTIONS = {
    "eta": (
        "To predict shipment ETA, please provide:\n"
        "- delivery_user_id (courier ID, integer)\n"
        "- from_dipan_id (hub / dipan ID, integer)\n"
        "- aoi_id (area ID, integer)\n"
        "- receipt_time (ISO datetime, e.g. 2024-10-12T14:30:00)\n"
        "- receipt_lat, receipt_lng (pickup coordinates)\n"
        "- poi_lat, poi_lng (delivery coordinates)"
    ),
    "next_stop": (
        "To predict the next stop, please provide:\n"
        "- current_lat, current_lng (courier position)\n"
        "- route_start_time (ISO datetime)\n"
        "- stops_completed (integer, optional, default 0)\n"
        "- remaining_orders: list of stops, each with order_id, poi_lat, poi_lng, "
        "receipt_time, receipt_lat, receipt_lng, city_name, typecode, aoi_id"
    ),
    "route": (
        "To predict a visit sequence, please provide:\n"
        "- orders: list of stops, each with order_id, poi_lat, poi_lng, "
        "receipt_time, receipt_lat, receipt_lng, city_name, typecode, aoi_id"
    ),
}


@dataclass
class PayloadResolution:
    ready: bool
    payload: dict[str, Any] | None
    missing: list[str]
    question: str | None
    partial_payload: dict[str, Any] | None = None


def _ensure_env() -> None:
    global _env_loaded
    if not _env_loaded:
        load_env()
        _env_loaded = True


def _llm_client() -> OpenAI:
    global _client
    _ensure_env()
    if _client is None:
        _client = OpenAI(
            api_key=os.getenv("NVIDIA_API_KEY"),
            base_url="https://integrate.api.nvidia.com/v1",
        )
    return _client


def _ensure_eta_import() -> None:
    path = str(ETA_SRC)
    if path not in sys.path:
        sys.path.insert(0, path)


def _ensure_route_import() -> None:
    path = str(ROUTE_ROOT)
    if path not in sys.path:
        sys.path.insert(0, path)


def _model_for_task(task: str) -> type[BaseModel]:
    if task == "eta":
        _ensure_eta_import()
        from eta_inference import ETARequest

        return ETARequest
    _ensure_route_import()
    from ml_services.route_prediction.schemas import NextStopRequest, RouteSequenceRequest

    if task == "next_stop":
        return NextStopRequest
    if task == "route":
        return RouteSequenceRequest
    raise ValueError(f"Unknown ML task: {task}")


def schema_for_task(task: str) -> dict[str, Any]:
    return _model_for_task(task).model_json_schema()


def _validation_missing(exc: ValidationError) -> list[str]:
    missing: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(part) for part in err["loc"])
        msg = err.get("msg", "invalid")
        missing.append(f"{loc}: {msg}")
    return missing


def _validate_payload(task: str, data: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    model_cls = _model_for_task(task)
    try:
        validated = model_cls.model_validate(data)
    except ValidationError as exc:
        return None, _validation_missing(exc)
    return validated.model_dump(mode="json"), []


def _extract_json_from_llm(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return json.loads(text)


def _query_has_actionable_values(user_query: str) -> bool:
    """True when the message likely contains concrete field values (not just intent)."""
    if re.search(r"\d", user_query):
        return True
    if "{" in user_query and "}" in user_query:
        return True
    return False


def _float_variants(value: float) -> list[str]:
    variants = [f"{value:g}", f"{value:.6f}", f"{value:.4f}", f"{value:.2f}"]
    seen: set[str] = set()
    out: list[str] = []
    for item in variants:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _value_grounded_in_text(value: Any, text: str) -> bool:
    if value is None:
        return False
    if isinstance(value, dict):
        return all(_value_grounded_in_text(v, text) for v in value.values())
    if isinstance(value, list):
        if not value:
            return False
        return all(_value_grounded_in_text(item, text) for item in value)

    text_norm = text.lower()
    if isinstance(value, bool):
        return str(value).lower() in text_norm
    if isinstance(value, int):
        return re.search(rf"(?<!\d){re.escape(str(value))}(?!\d)", text) is not None
    if isinstance(value, float):
        for candidate in _float_variants(value):
            if candidate in text or candidate in text_norm:
                return True
        return False
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return False
        if stripped.lower() in text_norm:
            return True
        for token in re.findall(r"\d+", stripped):
            if len(token) >= 4 and token in text:
                return True
        return False
    return str(value) in text


def _path_in_prior(path: tuple[str | int, ...], prior: dict[str, Any]) -> bool:
    node: Any = prior
    for part in path:
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return True


def _strip_ungrounded(
    data: dict[str, Any],
    user_query: str,
    prior: dict[str, Any] | None,
) -> dict[str, Any]:
    """Drop fields not present in user text unless they were already collected."""

    prior = prior or {}

    def walk(obj: Any, path: tuple[str | int, ...]) -> Any:
        if isinstance(obj, dict):
            kept: dict[str, Any] = {}
            for key, val in obj.items():
                child_path = (*path, key)
                if _path_in_prior(child_path, prior):
                    kept[key] = walk(val, child_path)
                elif _value_grounded_in_text(val, user_query):
                    kept[key] = walk(val, child_path)
            return kept
        if isinstance(obj, list):
            return [walk(item, (*path, idx)) for idx, item in enumerate(obj)]
        return obj

    return walk(data, ())


def _llm_extract_payload(
    task: str,
    user_query: str,
    prior_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    schema = schema_for_task(task)
    label = TASK_LABELS.get(task, task)
    prior_block = ""
    if prior_payload:
        prior_block = (
            "\nPreviously collected fields (only keep these; add new keys from the "
            "latest message when explicitly stated):\n"
            f"{json.dumps(prior_payload, indent=2, default=str)}\n"
        )

    prompt = f"""
You help build a JSON request body for {label}.

JSON Schema for the request body:
{json.dumps(schema, indent=2)}

User message:
{user_query}
{prior_block}

Rules:
1. Return a single JSON object only (no markdown).
2. Include ONLY values explicitly stated in the user message or prior payload.
3. If a required field is not stated, OMIT that key entirely.
4. NEVER use example, placeholder, or default values (e.g. 12345, 67890, round coordinates).
5. Use ISO-8601 strings for date-time fields.
6. For nested order lists, include an order object only when the user gave that stop's details.

Return only the request JSON object.
"""

    response = _llm_client().chat.completions.create(
        model=os.getenv("GRAPH_LLM_MODEL", "meta/llama-3.1-8b-instruct"),
        messages=[
            {
                "role": "system",
                "content": (
                    "You extract structured ML API payloads. "
                    "Never invent values. Output valid JSON only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        max_tokens=2000,
    )
    return _extract_json_from_llm(response.choices[0].message.content or "{}")


def _llm_clarification_question(
    task: str,
    user_query: str,
    partial: dict[str, Any],
    missing: list[str],
) -> str:
    label = TASK_LABELS.get(task, task)
    prompt = f"""
The user asked about {label}.

We have this partial JSON payload:
{json.dumps(partial, indent=2, default=str)}

These fields are still missing or invalid:
{json.dumps(missing, indent=2)}

User message:
{user_query}

Write a short, friendly message asking the user for the missing information.
List concrete field names and simple examples (types/units).
Do not mention JSON Schema or internal APIs.
"""

    response = _llm_client().chat.completions.create(
        model=os.getenv("GRAPH_LLM_MODEL", "meta/llama-3.1-8b-instruct"),
        messages=[
            {
                "role": "system",
                "content": "You ask clear follow-up questions to complete structured logistics ML requests.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=500,
    )
    return (response.choices[0].message.content or "").strip()


def resolve_ml_payload(
    task: str,
    user_query: str,
    prior_payload: dict[str, Any] | None = None,
) -> PayloadResolution:
    """
    Extract and validate an ML request payload from natural language.

    Returns a ready resolution when Pydantic validation passes; otherwise
    returns missing field paths and a user-facing clarification question.
    """
    if not prior_payload and not _query_has_actionable_values(user_query):
        return PayloadResolution(
            ready=False,
            payload=None,
            missing=["all required fields: not provided in user message"],
            question=_TEMPLATE_QUESTIONS.get(
                task,
                "Please provide the required shipment details for this prediction.",
            ),
            partial_payload={},
        )

    try:
        extracted = _llm_extract_payload(task, user_query, prior_payload)
    except (json.JSONDecodeError, Exception) as exc:
        return PayloadResolution(
            ready=False,
            payload=None,
            missing=[f"extraction_failed: {exc}"],
            question=(
                "I could not parse the request fields from your message. "
                "Please provide the shipment details needed for this prediction "
                "(IDs, coordinates, and times)."
            ),
            partial_payload=prior_payload,
        )

    merged = dict(prior_payload or {})
    _deep_merge(merged, extracted)
    merged = _strip_ungrounded(merged, user_query, prior_payload)

    payload, missing = _validate_payload(task, merged)
    if payload is not None:
        return PayloadResolution(
            ready=True,
            payload=payload,
            missing=[],
            question=None,
            partial_payload=None,
        )

    question = _TEMPLATE_QUESTIONS.get(task)
    if merged:
        try:
            question = _llm_clarification_question(task, user_query, merged, missing)
        except Exception:
            question = (
                "I need a few more details to run this prediction. "
                f"Please provide: {', '.join(missing)}"
            )
    elif not question:
        question = "Please provide the required shipment details for this prediction."

    return PayloadResolution(
        ready=False,
        payload=None,
        missing=missing,
        question=question,
        partial_payload=merged,
    )


def _deep_merge(base: dict[str, Any], update: dict[str, Any]) -> None:
    for key, value in update.items():
        if value is None:
            continue
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, dict)
        ):
            _deep_merge(base[key], value)
        else:
            base[key] = value
