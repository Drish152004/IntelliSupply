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
- hub_lookup: list hubs (optionally filtered by city); not single-hub detail lookup
- city_lookup: list cities with hubs

Rules:
- Inventory excludes shipments, couriers, routes, ETAs.
- Use confidence < 0.70 when the query is too vague.
- confidence must be between 0 and 1."""

_ETA_QUERY_SIGNALS: tuple[str, ...] = (
    "eta",
    "arrival time",
    "delivery time",
    "expected delivery",
    "expected arrival",
    "when will",
    "how long",
    "receipt time",
    "delivery estimate",
    "arrival estimate",
    "delivered by",
    "arriving",
    "arrive",
    "arrival",
    "delivers",
)

_CITY_LIST_QUERY_PATTERN = re.compile(
    r"\b(?:"
    r"city\s+list|list\s+cities|all\s+cities|which\s+cities|get\s+cities|"
    r"enumerate\s+cities|show\s+cities|cities\s+pls"
    r")\b",
    re.I,
)

_COURIER_ORDERS_QUERY_PHRASES: tuple[str, ...] = (
    "assigned orders",
    "courier orders",
)

_COURIER_ORDERS_QUERY_PATTERN = re.compile(r"\b(?:orders?|shipments?)\b", re.I)

_COURIER_ROUTE_QUERY_PHRASES: tuple[str, ...] = (
    "route for",
    "courier route",
    "show route",
    "planned route",
    "assigned route",
)

_COURIER_ROUTE_QUERY_PATTERN = re.compile(r"\broute\b", re.I)

_HUB_LIST_QUERY_PATTERN = re.compile(
    r"\b(?:"
    r"list\s+hubs|show\s+hubs|which\s+hubs|get\s+hubs|enumerate\s+hubs"
    r")\b",
    re.I,
)


def _normalize_logistics_abbreviations(user_query: str) -> str:
    """Expand obvious logistics abbreviations before deterministic routing."""
    normalized = user_query
    normalized = re.sub(r"\bnxt\s+stop\b", "next stop", normalized, flags=re.I)
    normalized = re.sub(r"\bnext\s+stp\b", "next stop", normalized, flags=re.I)
    normalized = re.sub(r"\bnxt\s+stp\b", "next stop", normalized, flags=re.I)
    normalized = re.sub(r"\brt\b", "route", normalized, flags=re.I)
    return normalized


def _is_eta_query(query: str) -> bool:
    lowered = query.lower()
    return any(signal in lowered for signal in _ETA_QUERY_SIGNALS)


def _is_city_list_query(query: str) -> bool:
    lowered = query.lower().strip()
    if lowered == "cities":
        return True
    return _CITY_LIST_QUERY_PATTERN.search(lowered) is not None


def _is_hub_list_query(query: str) -> bool:
    """True when the user asks to list hubs (all or in a city), not a single hub."""
    lowered = query.lower().strip()
    if lowered == "hubs":
        return True
    if _HUB_LIST_QUERY_PATTERN.search(lowered):
        return True
    return "hubs" in lowered and " in " in lowered


def _is_courier_orders_query(query: str) -> bool:
    """True when the user asks for orders/shipments assigned to a courier."""
    lowered = query.lower()
    if any(phrase in lowered for phrase in _COURIER_ORDERS_QUERY_PHRASES):
        return True
    return _COURIER_ORDERS_QUERY_PATTERN.search(lowered) is not None


def _is_courier_route_query(query: str) -> bool:
    """True when the user asks for a courier's route."""
    lowered = query.lower()
    if "next stop" in lowered:
        return False
    if any(phrase in lowered for phrase in _COURIER_ROUTE_QUERY_PHRASES):
        return True
    return _COURIER_ROUTE_QUERY_PATTERN.search(lowered) is not None


def _is_courier_route_entity_match(query: str, entities: dict[str, str]) -> bool:
    """Courier route when courier_id is present without order or hub-pair scope."""
    if not entities.get("courier_id"):
        return False
    if entities.get("order_id") or entities.get("shipment_id"):
        return False
    if entities.get("from_hub") or entities.get("to_hub"):
        return False
    return _is_courier_route_query(query)


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


def _deterministic_entity_routing(
    user_query: str,
    entities: dict[str, str],
    domain_hint: str | None = None,
) -> dict[str, Any] | None:
    """Route using extracted entities before keyword or LLM classification."""
    query = user_query.lower()

    if domain_hint == "inventory" or any(
        entities.get(key) for key in ("sku_id", "warehouse_id", "product_name")
    ):
        inventory_score = sum(1 for keyword in INVENTORY_KEYWORDS if keyword in query)
        logistics_score = sum(1 for keyword in LOGISTICS_KEYWORDS if keyword in query)
        if domain_hint == "inventory" or inventory_score >= logistics_score:
            return {
                "domain": "inventory",
                "task": "inventory_nlsql",
                "confidence": 0.92,
                "source": "entity_routing",
            }

    if entities.get("order_id") or entities.get("shipment_id"):
        if _is_eta_query(query):
            return {
                "domain": "logistics",
                "task": "eta_lookup",
                "confidence": 0.94,
                "source": "entity_routing",
            }
        if "route" in query:
            return {
                "domain": "logistics",
                "task": "route_lookup",
                "confidence": 0.91,
                "source": "entity_routing",
            }
        return {
            "domain": "logistics",
            "task": "shipment_lookup",
            "confidence": 0.95,
            "source": "entity_routing",
        }

    if entities.get("courier_id") and _is_courier_orders_query(query):
        return {
            "domain": "logistics",
            "task": "shipment_lookup",
            "confidence": 0.93,
            "source": "entity_routing",
        }

    if entities.get("courier_id") and "hub" in query:
        return {
            "domain": "logistics",
            "task": "courier_lookup",
            "confidence": 0.92,
            "source": "entity_routing",
        }

    if entities.get("courier_id") and _is_eta_query(query):
        return {
            "domain": "logistics",
            "task": "eta_lookup",
            "confidence": 0.92,
            "source": "entity_routing",
        }

    if (
        entities.get("courier_id")
        and "courier" in query
        and not _is_courier_orders_query(query)
        and "route" not in query
        and not (entities.get("from_hub") or entities.get("to_hub"))
    ):
        return {
            "domain": "logistics",
            "task": "courier_lookup",
            "confidence": 0.91,
            "source": "entity_routing",
        }

    if entities.get("from_hub") and entities.get("to_hub"):
        return {
            "domain": "logistics",
            "task": "route_lookup",
            "confidence": 0.93,
            "source": "entity_routing",
        }

    if entities.get("to_hub") and (
        entities.get("from_hub") or entities.get("hub_id") or "route" in query
    ):
        return {
            "domain": "logistics",
            "task": "route_lookup",
            "confidence": 0.93,
            "source": "entity_routing",
        }

    if entities.get("self_scoped") == "true" and "next stop" in query:
        return {
            "domain": "logistics",
            "task": "next_stop_lookup",
            "confidence": 0.90,
            "source": "entity_routing",
        }

    if _is_courier_route_entity_match(query, entities):
        return {
            "domain": "logistics",
            "task": "courier_route_lookup",
            "confidence": 0.92,
            "source": "entity_routing",
        }

    if entities.get("self_scoped") == "true" and "route" in query:
        return {
            "domain": "logistics",
            "task": "courier_route_lookup",
            "confidence": 0.90,
            "source": "entity_routing",
        }

    if entities.get("city_name") and _is_hub_list_query(query):
        return {
            "domain": "logistics",
            "task": "hub_lookup",
            "confidence": 0.88,
            "source": "entity_routing",
        }

    return None


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

    if _is_city_list_query(query):
        return {"domain": "logistics", "task": "city_lookup", "confidence": 0.88}

    if _is_hub_list_query(query):
        return {"domain": "logistics", "task": "hub_lookup", "confidence": 0.85}

    if "courier" in query and _is_courier_orders_query(query):
        return {"domain": "logistics", "task": "shipment_lookup", "confidence": 0.88}

    if "courier" in query and _is_courier_route_query(query):
        return {"domain": "logistics", "task": "courier_route_lookup", "confidence": 0.88}

    if "courier" in query and "hub" in query:
        return {"domain": "logistics", "task": "courier_lookup", "confidence": 0.78}

    if "courier" in query:
        return {"domain": "logistics", "task": "courier_lookup", "confidence": 0.78}

    inventory_score = sum(1 for keyword in INVENTORY_KEYWORDS if keyword in query)
    logistics_score = sum(1 for keyword in LOGISTICS_KEYWORDS if keyword in query)

    if domain_hint == "inventory" and inventory_score >= logistics_score:
        return {"domain": "inventory", "task": "inventory_nlsql", "confidence": 0.80}

    if domain_hint == "logistics" and logistics_score >= inventory_score and logistics_score > 0:
        return {"domain": "logistics", "task": "shipment_lookup", "confidence": 0.75}

    if inventory_score > logistics_score and inventory_score > 0:
        return {"domain": "inventory", "task": "inventory_nlsql", "confidence": 0.82}

    if "shipment" in query and any(p in query for p in ("where is", "status", "track", "my")):
        return {"domain": "logistics", "task": "shipment_lookup", "confidence": 0.82}

    if re.search(r"\bshipment\b", query) and len(words) <= 3:
        return {"domain": "logistics", "task": "shipment_lookup", "confidence": 0.55}

    if _is_eta_query(query) or "my eta" in query:
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


def classify_domain_task(
    user_query: str,
    entities: dict[str, str] | None = None,
    domain_hint: str | None = None,
) -> dict[str, Any]:
    resolved_entities = entities or {}
    routing_query = _normalize_logistics_abbreviations(user_query)

    entity_route = _deterministic_entity_routing(
        routing_query,
        resolved_entities,
        domain_hint=domain_hint,
    )
    if entity_route:
        return entity_route

    keyword_route = _keyword_fallback(routing_query, domain_hint=domain_hint)
    if keyword_route.get("confidence", 0) >= CONFIDENCE_THRESHOLD:
        return {**keyword_route, "source": "keyword_fallback"}

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
            return {**parsed, "source": "llm_classifier"}
    except Exception:
        logger.exception("Classifier LLM call failed; using keyword fallback")

    return {**_keyword_fallback(routing_query, domain_hint=domain_hint), "source": "keyword_fallback"}
