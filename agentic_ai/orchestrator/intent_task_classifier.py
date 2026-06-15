"""
Domain and task classification for the orchestration layer.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from integrations.llm_client import get_client, get_model
from orchestrator.task_registry import (
    CONFIDENCE_THRESHOLD,
    DOMAIN_TASK_MAP,
    EXTREME_LOW_CONFIDENCE_THRESHOLD,
    INVENTORY_KEYWORDS,
    LOGISTICS_KEYWORDS,
    TASKS_BYPASS_INTENT_CLARIFICATION,
    VALID_DOMAINS,
    VALID_TASKS,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You classify user messages for IntelliSupply's orchestrator.

Return ONLY valid JSON with exactly these keys:
{"domain": "...", "task": "...", "confidence": 0.0-1.0}

Domains:
- inventory: products, stock levels, warehouse analytics (Postgres inventory DB)
- logistics: shipments, routes, ETAs, couriers, hubs, cities (Aura graph)

Inventory task:
- inventory_nlsql

Logistics retrieval tasks:
- shipment_lookup: shipment/order status or location
- route_lookup: assigned route for an order or hub pair
- eta_lookup: delivery timing / receipt time for order or courier
- courier_lookup: courier profile, hub assignment
- next_stop_lookup: next stop on a courier's saved route
- courier_route_lookup: full saved route sequence for a courier/day
- hub_lookup: list hubs (optionally in a city)
- city_lookup: list cities with hubs

Rules:
- Inventory excludes shipments, couriers, routes, ETAs.
- Use confidence < 0.70 when the query is too vague.
- confidence must be between 0 and 1."""

FEW_SHOT_EXAMPLES: list[tuple[str, dict[str, Any]]] = [
    ("How many iPhones are in Shanghai?", {"domain": "inventory", "task": "inventory_nlsql", "confidence": 0.95}),
    ("Where is shipment ord-abc?", {"domain": "logistics", "task": "shipment_lookup", "confidence": 0.93}),
    ("What route was assigned for order ord-abc?", {"domain": "logistics", "task": "route_lookup", "confidence": 0.91}),
    ("What is the ETA for order ord-abc?", {"domain": "logistics", "task": "eta_lookup", "confidence": 0.94}),
    ("Which hub is courier C55 assigned to?", {"domain": "logistics", "task": "courier_lookup", "confidence": 0.92}),
    ("What is my next stop?", {"domain": "logistics", "task": "next_stop_lookup", "confidence": 0.90}),
    ("Show my route for today", {"domain": "logistics", "task": "courier_route_lookup", "confidence": 0.90}),
    ("List hubs in Chongqing", {"domain": "logistics", "task": "hub_lookup", "confidence": 0.88}),
    ("List all cities", {"domain": "logistics", "task": "city_lookup", "confidence": 0.87}),
]


def _build_messages(user_query: str, domain_hint: str | None = None) -> list[dict[str, str]]:
    hint = ""
    if domain_hint in VALID_DOMAINS:
        hint = f"\nRouting hint: the query likely concerns the {domain_hint} domain."
    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT + hint}]
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


def _keyword_fallback(user_query: str, domain_hint: str | None = None) -> dict[str, Any]:
    query = user_query.lower().strip()
    words = query.split()

    if "next stop" in query or "my next stop" in query:
        return {"domain": "logistics", "task": "next_stop_lookup", "confidence": 0.85}

    if "my route" in query or "courier route" in query:
        return {"domain": "logistics", "task": "courier_route_lookup", "confidence": 0.85}

    if "list cities" in query or "all cities" in query or query.strip() == "cities":
        return {"domain": "logistics", "task": "city_lookup", "confidence": 0.88}

    if "list hubs" in query or "show hubs" in query or ("hubs" in query and "in" in query):
        return {"domain": "logistics", "task": "hub_lookup", "confidence": 0.85}

    inventory_score = sum(1 for keyword in INVENTORY_KEYWORDS if keyword in query)
    logistics_score = sum(1 for keyword in LOGISTICS_KEYWORDS if keyword in query)

    if domain_hint == "inventory" and inventory_score >= logistics_score:
        return {"domain": "inventory", "task": "inventory_nlsql", "confidence": 0.80}

    if domain_hint == "logistics" and logistics_score >= inventory_score and logistics_score > 0:
        return {"domain": "logistics", "task": "shipment_lookup", "confidence": 0.75}

    if inventory_score > logistics_score and inventory_score > 0:
        return {"domain": "inventory", "task": "inventory_nlsql", "confidence": 0.82}

    if "courier" in query and "hub" in query:
        return {"domain": "logistics", "task": "courier_lookup", "confidence": 0.78}

    if "courier" in query:
        return {"domain": "logistics", "task": "courier_lookup", "confidence": 0.78}

    if "shipment" in query and any(p in query for p in ("where is", "status", "track", "my")):
        return {"domain": "logistics", "task": "shipment_lookup", "confidence": 0.82}

    if re.search(r"\bshipment\b", query) and len(words) <= 3:
        return {"domain": "logistics", "task": "shipment_lookup", "confidence": 0.55}

    if "eta" in query or "my eta" in query:
        return {"domain": "logistics", "task": "eta_lookup", "confidence": 0.82}

    if "route" in query:
        return {"domain": "logistics", "task": "route_lookup", "confidence": 0.72}

    if logistics_score > 0:
        return {"domain": "logistics", "task": "shipment_lookup", "confidence": 0.60}

    return {"domain": "logistics", "task": "shipment_lookup", "confidence": 0.50}


def needs_intent_clarification(task: str, confidence: float) -> bool:
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
    from context.clarification_manager import ClarificationManager

    query = user_query.lower().strip()

    if "next stop" in query:
        return "Are you asking for your next stop or a specific courier's next stop?"

    if re.search(r"\bshipment\b", query):
        return "Are you looking for shipment status, ETA, route, or courier assignment?"

    if "courier" in query:
        return "Do you need courier details, their route, shipments, or next stop?"

    if "route" in query and "eta" not in query:
        return "Do you want an order route, your courier route, or a next stop?"

    if "hub" in query or "city" in query:
        return "Do you want a list of cities, hubs in a city, or logistics status for an order?"

    if classification and classification.get("domain") == "inventory":
        return "Could you clarify which product or warehouse you want inventory information for?"

    return ClarificationManager.intent_question()


def classify_domain_task(user_query: str, domain_hint: str | None = None) -> dict[str, Any]:
    try:
        response = get_client().chat.completions.create(
            model=get_model(),
            messages=_build_messages(user_query, domain_hint=domain_hint),
            temperature=0.0,
            max_tokens=128,
        )
        raw = response.choices[0].message.content or ""
        parsed = _parse_classifier_response(raw)
        if parsed:
            return parsed
    except Exception:
        logger.exception("Classifier LLM call failed; using keyword fallback")

    return _keyword_fallback(user_query, domain_hint=domain_hint)
