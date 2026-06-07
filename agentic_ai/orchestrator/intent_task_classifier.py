"""
Domain and task classification for the orchestration layer.

Uses the shared LLM client to classify user queries into inventory or logistics
domains and a specific task, with confidence scoring and safe fallbacks.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from integrations.llm_client import get_client, get_model

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.70
EXTREME_LOW_CONFIDENCE_THRESHOLD = 0.30

# Known tasks that defer clarification to query completeness / context resolution.
TASKS_BYPASS_INTENT_CLARIFICATION: frozenset[str] = frozenset({
    "inventory_nlsql",
    "demand_forecast",
    "eta_prediction",
    "route_prediction",
    "shipment_lookup",
    "courier_lookup",
})

VALID_DOMAINS = frozenset({"inventory", "logistics"})

INVENTORY_TASKS = frozenset({"inventory_nlsql"})

LOGISTICS_TASKS = frozenset({
    "eta_lookup",
    "eta_prediction",
    "route_lookup",
    "route_prediction",
    "next_stop_prediction",
    "shipment_lookup",
    "courier_lookup",
    "demand_forecast",
})

VALID_TASKS = INVENTORY_TASKS | LOGISTICS_TASKS

DOMAIN_TASK_MAP: dict[str, frozenset[str]] = {
    "inventory": INVENTORY_TASKS,
    "logistics": LOGISTICS_TASKS,
}

SYSTEM_PROMPT = """You classify user messages for IntelliSupply's orchestrator.

Return ONLY valid JSON with exactly these keys:
{"domain": "...", "task": "...", "confidence": 0.0-1.0}

Domains (only two):
- inventory: products, hubs, stock levels, inventory availability, inventory analytics
- logistics: shipments, routes, ETAs, couriers, delivery predictions, demand forecasting

Inventory has ONE task:
- inventory_nlsql

Logistics tasks:
- eta_lookup: user wants an existing ETA (e.g. "What is the ETA for order O123?")
- eta_prediction: user wants a new ETA prediction (e.g. "Predict ETA from Hub A to Hub B")
- route_lookup: user wants an already generated route (e.g. "What route was assigned?")
- route_prediction: user wants a new route prediction (e.g. "Generate route for order O123")
- next_stop_prediction: courier next stop (e.g. "What is courier 55's next stop?")
- shipment_lookup: shipment status/location (e.g. "Where is shipment SH123?")
- courier_lookup: courier info (e.g. "Show courier 55", "Which hub is courier 55 assigned to?")
- demand_forecast: delivery demand forecasting (e.g. "Forecast delivery demand next week")

Rules:
- Inventory does NOT include ETA, routes, couriers, or demand forecasting.
- Use confidence < 0.70 when the query is too vague to pick a single task.
- confidence must be a number between 0 and 1."""

FEW_SHOT_EXAMPLES: list[tuple[str, dict[str, Any]]] = [
    (
        "How many iPhones are in Shanghai?",
        {"domain": "inventory", "task": "inventory_nlsql", "confidence": 0.95},
    ),
    (
        "How many shipments are there between hub 1 and hub 2?",
        {"domain": "logistics", "task": "shipment_lookup", "confidence": 0.88},
    ),
    (
        "Forecast delivery demand next week",
        {"domain": "logistics", "task": "demand_forecast", "confidence": 0.95},
    ),
    (
        "What is the ETA for order O123?",
        {"domain": "logistics", "task": "eta_lookup", "confidence": 0.94},
    ),
    (
        "Predict ETA from Hub A to Hub B",
        {"domain": "logistics", "task": "eta_prediction", "confidence": 0.93},
    ),
    (
        "Predict route for order O123",
        {"domain": "logistics", "task": "route_prediction", "confidence": 0.92},
    ),
    (
        "What route was predicted for order O123?",
        {"domain": "logistics", "task": "route_lookup", "confidence": 0.91},
    ),
    (
        "Where is shipment SH123?",
        {"domain": "logistics", "task": "shipment_lookup", "confidence": 0.93},
    ),
    (
        "Which hub is courier 55 assigned to?",
        {"domain": "logistics", "task": "courier_lookup", "confidence": 0.92},
    ),
    (
        "shipment 123",
        {"domain": "logistics", "task": "shipment_lookup", "confidence": 0.45},
    ),
]

INVENTORY_KEYWORDS = (
    "stock",
    "inventory",
    "warehouse",
    "hub",
    "product",
    "available",
    "laptop",
    "laptops",
    "iphone",
    "iphones",
    "how many",
)

LOGISTICS_KEYWORDS = (
    "shipment",
    "route",
    "delivery",
    "eta",
    "transport",
    "courier",
    "forecast",
    "predict",
)


def _build_messages(user_query: str) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for question, label in FEW_SHOT_EXAMPLES:
        messages.append({"role": "user", "content": question})
        messages.append({"role": "assistant", "content": json.dumps(label)})
    messages.append({"role": "user", "content": user_query})
    return messages


def _coerce_confidence(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, score))


def _normalize_result(raw: dict[str, Any]) -> dict[str, Any] | None:
    domain = str(raw.get("domain", "")).strip().lower()
    task = str(raw.get("task", "")).strip().lower()
    confidence = _coerce_confidence(raw.get("confidence", 0.5))

    if domain not in VALID_DOMAINS or task not in VALID_TASKS:
        return None
    if task not in DOMAIN_TASK_MAP[domain]:
        return None
    return {"domain": domain, "task": task, "confidence": confidence}


def _extract_json_object(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[^{}]*\}", cleaned, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


def _parse_classifier_response(text: str) -> dict[str, Any] | None:
    payload = _extract_json_object(text)
    if not payload:
        return None
    return _normalize_result(payload)


def _keyword_fallback(user_query: str) -> dict[str, Any]:
    query = user_query.lower().strip()
    words = query.split()

    inventory_score = sum(1 for keyword in INVENTORY_KEYWORDS if keyword in query)
    logistics_score = sum(1 for keyword in LOGISTICS_KEYWORDS if keyword in query)

    if inventory_score > logistics_score and inventory_score > 0:
        return {"domain": "inventory", "task": "inventory_nlsql", "confidence": 0.82}

    if re.search(r"\bhow many\b", query) and "shipment" in query:
        return {"domain": "logistics", "task": "shipment_lookup", "confidence": 0.85}

    if "next stop" in query or ("next" in query and "stop" in query):
        return {"domain": "logistics", "task": "next_stop_prediction", "confidence": 0.75}

    if any(phrase in query for phrase in ("demand forecast", "forecast delivery", "forecast demand")):
        return {"domain": "logistics", "task": "demand_forecast", "confidence": 0.80}

    if "forecast" in query or ("predict" in query and "deliver" in query):
        return {"domain": "logistics", "task": "demand_forecast", "confidence": 0.75}

    if "courier" in query:
        return {"domain": "logistics", "task": "courier_lookup", "confidence": 0.78}

    if re.search(r"\bshipment\b", query) and len(words) <= 3:
        return {"domain": "logistics", "task": "shipment_lookup", "confidence": 0.55}

    if "shipment" in query and any(
        phrase in query for phrase in ("where is", "status", "track", "location")
    ):
        return {"domain": "logistics", "task": "shipment_lookup", "confidence": 0.82}

    if "eta" in query:
        if any(word in query for word in ("predict", "estimate", "forecast")):
            return {"domain": "logistics", "task": "eta_prediction", "confidence": 0.80}
        return {"domain": "logistics", "task": "eta_lookup", "confidence": 0.82}

    if "route" in query:
        if any(word in query for word in ("predict", "generate", "optimize", "best")):
            return {"domain": "logistics", "task": "route_prediction", "confidence": 0.80}
        if any(phrase in query for phrase in ("was predicted", "was assigned", "show predicted")):
            return {"domain": "logistics", "task": "route_lookup", "confidence": 0.80}
        return {"domain": "logistics", "task": "route_lookup", "confidence": 0.72}

    if logistics_score > 0:
        return {"domain": "logistics", "task": "shipment_lookup", "confidence": 0.60}

    return {"domain": "logistics", "task": "shipment_lookup", "confidence": 0.50}


def needs_intent_clarification(task: str, confidence: float) -> bool:
    """
    Return True when the orchestrator should stop for intent-level clarification.

    Known logistics/ML tasks bypass the normal confidence threshold so HITL layers
    can ask task-specific questions. Clarification still triggers for unknown tasks
    or extremely low confidence.
    """
    if confidence < EXTREME_LOW_CONFIDENCE_THRESHOLD:
        return True
    if task in TASKS_BYPASS_INTENT_CLARIFICATION:
        return False
    if not task or task not in VALID_TASKS:
        return True
    if confidence < CONFIDENCE_THRESHOLD:
        return True
    return False


def build_clarification_question(user_query: str, classification: dict[str, Any] | None = None) -> str:
    """Build a contextual clarification question for low-confidence queries."""
    query = user_query.lower().strip()

    if re.search(r"\bshipment\b", query):
        return (
            "Are you looking for shipment status, ETA information, or route information?"
        )

    if "courier" in query:
        return (
            "Are you looking for courier details, the courier's next stop, "
            "or route information?"
        )

    if "route" in query and "eta" not in query:
        return (
            "Do you want to look up an existing route or generate a new route prediction?"
        )

    if "eta" in query or "delivery time" in query:
        return (
            "Do you want the current ETA for an order/shipment, or a new ETA prediction?"
        )

    if classification and classification.get("domain") == "inventory":
        return (
            "Could you clarify which product or hub you want inventory information for?"
        )

    return (
        "Could you clarify whether you need inventory/stock information "
        "or logistics help (shipments, routes, ETAs, couriers, or demand forecasts)?"
    )


def classify_domain_task(user_query: str) -> dict[str, Any]:
    """Classify a user query into domain, task, and confidence."""
    try:
        response = get_client().chat.completions.create(
            model=get_model(),
            messages=_build_messages(user_query),
            temperature=0.0,
            max_tokens=128,
        )
        raw = response.choices[0].message.content or ""
        parsed = _parse_classifier_response(raw)
        if parsed:
            logger.debug(
                "Classifier LLM result: domain=%s task=%s confidence=%s",
                parsed["domain"],
                parsed["task"],
                parsed["confidence"],
            )
            return parsed
    except Exception:
        logger.exception("Classifier LLM call failed; using keyword fallback")

    fallback = _keyword_fallback(user_query)
    logger.debug(
        "Classifier fallback result: domain=%s task=%s confidence=%s",
        fallback["domain"],
        fallback["task"],
        fallback["confidence"],
    )
    return fallback
