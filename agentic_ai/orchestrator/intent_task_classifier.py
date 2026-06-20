"""
Logistics task classification for the orchestration layer.

Domain ownership belongs entirely to coarse authorization. Inventory queries
bypass this node (coarse_authorization -> inventory_nlsql), so every query that
reaches intent is already logistics. This module therefore only selects which
logistics *task* should execute; it never classifies or overwrites the domain
and contains no inventory tasks, examples, or routing.

Pipeline:
  Entity extraction → candidate narrowing → LLM logistics task classification
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from integrations.llm_client import get_client, get_model
from orchestrator.intent_routing import narrow_candidate_tasks
from orchestrator.task_registry import (
    CONFIDENCE_THRESHOLD,
    EXTREME_LOW_CONFIDENCE_THRESHOLD,
    LOGISTICS_RETRIEVAL_TASKS,
)

logger = logging.getLogger(__name__)

# The only domain that reaches intent. Used as the hard domain pin so the task
# classifier can never relabel the turn's domain.
_LOGISTICS_DOMAIN = "logistics"

# Valid task outputs for the logistics-only classifier. inventory_nlsql is
# intentionally excluded: it is unreachable here and must never be selected.
_LOGISTICS_VALID_TASKS = frozenset(LOGISTICS_RETRIEVAL_TASKS)

INTENT_SYSTEM_PROMPT = """You are IntelliSupply's logistics task classifier.

Every query reaching this classifier has already been classified as logistics
by coarse authorization.

Your job is only to determine which logistics task should execute.

Never classify inventory tasks.
Never reclassify the domain.
Domain selection has already been completed.

Return ONLY valid JSON.

Schema:

{
"task": "<task>",
"confidence": <0.0-1.0>
}

Allowed tasks (logistics only):

order_lookup
courier_orders
courier_route
recent_routes
delivery_days
hub_route

Definitions:

order_lookup:
order status, route, courier assignment, ETA, order details

courier_orders:
orders assigned to courier, courier deliveries, courier workload

courier_route:
next stop, today's route, remaining stops, route sequence, optimized route

recent_routes:
recent deliveries, latest orders, newest routes

delivery_days:
available delivery dates or schedules

hub_route:
route between source and destination hubs

Rules:

* Choose exactly one task from the allowed logistics tasks.
* Never invent tasks. Never output inventory tasks.
* Use extracted entities as context.
* "next stop" ALWAYS means courier_route.
* "remaining stops" ALWAYS means courier_route.
* "today's route" ALWAYS means courier_route.
* "assigned orders" ALWAYS means courier_orders.
* "latest deliveries" ALWAYS means recent_routes.
* "available delivery dates" ALWAYS means delivery_days.
* Route between hubs ALWAYS means hub_route.
* Order ID questions generally mean order_lookup.
* If the query does not clearly match a logistics task, pick the closest one
  and set confidence below 0.70 so the system can ask for clarification.

Return JSON only."""

FEW_SHOT_EXAMPLES: list[tuple[str, dict[str, str], dict[str, Any]]] = [
    (
        "Where is order ORD123?",
        {"order_id": "ORD123"},
        {"task": "order_lookup", "confidence": 0.99},
    ),
    (
        "Who is handling ORD123?",
        {"order_id": "ORD123"},
        {"task": "order_lookup", "confidence": 0.99},
    ),
    (
        "What is the ETA for ORD123?",
        {"order_id": "ORD123"},
        {"task": "order_lookup", "confidence": 0.99},
    ),
    (
        "Show route for ORD123",
        {"order_id": "ORD123"},
        {"task": "order_lookup", "confidence": 0.99},
    ),
    (
        "What orders does John have?",
        {"courier_name": "John"},
        {"task": "courier_orders", "confidence": 0.98},
    ),
    (
        "Show deliveries assigned to courier C123",
        {"courier_id": "C123"},
        {"task": "courier_orders", "confidence": 0.98},
    ),
    (
        "What is John's next stop?",
        {"courier_name": "John"},
        {"task": "courier_route", "confidence": 0.99},
    ),
    (
        "Show today's route for John",
        {"courier_name": "John"},
        {"task": "courier_route", "confidence": 0.99},
    ),
    (
        "What deliveries remain for courier C123?",
        {"courier_id": "C123"},
        {"task": "courier_route", "confidence": 0.98},
    ),
    (
        "Show recent deliveries",
        {},
        {"task": "recent_routes", "confidence": 0.95},
    ),
    (
        "Show latest orders",
        {},
        {"task": "recent_routes", "confidence": 0.95},
    ),
    (
        "Which delivery dates exist?",
        {},
        {"task": "delivery_days", "confidence": 0.95},
    ),
    (
        "Show available delivery schedules",
        {},
        {"task": "delivery_days", "confidence": 0.95},
    ),
    (
        "Route from Hub 2 to Hub 5",
        {"from_hub": "2", "to_hub": "5"},
        {"task": "hub_route", "confidence": 0.99},
    ),
]


def _normalize_logistics_abbreviations(user_query: str) -> str:
    """Expand obvious logistics abbreviations before classification."""
    normalized = user_query
    normalized = re.sub(r"\bnxt\s+stop\b", "next stop", normalized, flags=re.I)
    normalized = re.sub(r"\bnext\s+stp\b", "next stop", normalized, flags=re.I)
    normalized = re.sub(r"\bnxt\s+stp\b", "next stop", normalized, flags=re.I)
    normalized = re.sub(r"\brt\b", "route", normalized, flags=re.I)
    return normalized


def _build_intent_messages(
    user_query: str,
    entities: dict[str, str],
    candidate_tasks: list[str],
) -> list[dict[str, str]]:
    candidate_block = "\n".join(f"- {task}" for task in candidate_tasks)
    messages: list[dict[str, str]] = [{"role": "system", "content": INTENT_SYSTEM_PROMPT}]

    for question, example_entities, label in FEW_SHOT_EXAMPLES:
        if label["task"] not in candidate_tasks:
            continue
        messages.append(
            {
                "role": "user",
                "content": (
                    f"Query:\n{question}\n\n"
                    f"Entities:\n{json.dumps(example_entities)}\n\n"
                    f"Candidate tasks:\n{candidate_block}"
                ),
            }
        )
        messages.append({"role": "assistant", "content": json.dumps(label)})

    messages.append(
        {
            "role": "user",
            "content": (
                f"Query:\n{user_query}\n\n"
                f"Entities:\n{json.dumps(entities)}\n\n"
                f"Candidate tasks:\n{candidate_block}\n\n"
                "Choose exactly one task from the candidate list."
            ),
        }
    )
    return messages


def _coerce_confidence(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, score))


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


def _normalize_task_result(
    raw: dict[str, Any],
    *,
    candidate_tasks: list[str],
) -> dict[str, Any] | None:
    """Normalize the LLM output to a logistics task + confidence.

    The classifier returns only ``task`` and ``confidence``; domain is never
    derived from the task here. Any non-logistics task (e.g. inventory_nlsql)
    is rejected outright so it can never leak through.
    """
    task = str(raw.get("task", "")).strip().lower()
    confidence = _coerce_confidence(raw.get("confidence", 0.5))

    if task not in _LOGISTICS_VALID_TASKS:
        logger.warning("LLM returned non-logistics task %s; rejecting", task)
        return None
    if task not in candidate_tasks:
        logger.warning("LLM chose task %s outside candidates %s", task, candidate_tasks)
        if len(candidate_tasks) == 1:
            task = candidate_tasks[0]
            confidence = min(confidence, 0.65)
        else:
            confidence = min(confidence, 0.55)

    return {"task": task, "confidence": confidence}


def _parse_intent_response(
    text: str,
    *,
    candidate_tasks: list[str],
) -> dict[str, Any] | None:
    payload = _extract_json_object(text)
    if not payload:
        return None
    return _normalize_task_result(payload, candidate_tasks=candidate_tasks)


def _keyword_fallback_task(
    user_query: str,
    *,
    candidate_tasks: list[str],
    domain: str,
) -> dict[str, Any]:
    """Last-resort task guess when LLM classification fails."""
    query = user_query.lower().strip()
    candidates = set(candidate_tasks)

    def _pick(task: str, confidence: float) -> dict[str, Any]:
        if task not in candidates:
            if len(candidate_tasks) == 1:
                task = candidate_tasks[0]
                confidence = min(confidence, 0.55)
            else:
                task = candidate_tasks[0]
                confidence = 0.45
        return {
            "domain": domain,
            "task": task,
            "confidence": confidence,
        }

    if "next stop" in query and "courier_route" in candidates:
        return _pick("courier_route", 0.85)

    if any(phrase in query for phrase in ("remaining stops", "today's route", "my route")):
        if "courier_route" in candidates:
            return _pick("courier_route", 0.80)

    if any(phrase in query for phrase in ("assigned orders", "orders assigned", "courier workload")):
        if "courier_orders" in candidates:
            return _pick("courier_orders", 0.78)

    if any(phrase in query for phrase in ("recent deliveries", "latest orders", "newest routes")):
        if "recent_routes" in candidates:
            return _pick("recent_routes", 0.78)

    if any(phrase in query for phrase in ("delivery dates", "delivery schedules", "available delivery")):
        if "delivery_days" in candidates:
            return _pick("delivery_days", 0.78)

    if "route" in query and "hub_route" in candidates and (" from " in query or " to " in query):
        return _pick("hub_route", 0.72)

    if any(signal in query for signal in ("eta", "arrival", "delivery time", "order ")):
        if "order_lookup" in candidates:
            return _pick("order_lookup", 0.62)

    if "courier" in query and "courier_orders" in candidates:
        return _pick("courier_orders", 0.55)

    return _pick(candidate_tasks[0], 0.45)


def _classify_with_llm(
    user_query: str,
    entities: dict[str, str],
    candidate_tasks: list[str],
) -> dict[str, Any] | None:
    try:
        response = get_client().chat.completions.create(
            model=get_model(),
            messages=_build_intent_messages(user_query, entities, candidate_tasks),
            temperature=0.0,
            max_tokens=128,
        )
        raw = response.choices[0].message.content or ""
        return _parse_intent_response(raw, candidate_tasks=candidate_tasks)
    except Exception:
        logger.exception("Intent classifier LLM call failed")
        return None


def needs_intent_clarification(task: str, confidence: float) -> bool:
    if confidence < EXTREME_LOW_CONFIDENCE_THRESHOLD:
        return True
    if not task or task not in _LOGISTICS_VALID_TASKS:
        return True
    if confidence < CONFIDENCE_THRESHOLD:
        return True
    return False


def build_clarification_question(user_query: str, classification: dict[str, Any] | None = None) -> str:
    from context.clarification_manager import ClarificationManager

    query = user_query.lower().strip()

    if "next stop" in query or "remaining stops" in query:
        return "Are you asking for a courier's next stop or their full route for today?"

    if re.search(r"\border\b", query):
        return (
            "Are you looking for order details, orders assigned to a courier, "
            "or recent deliveries?"
        )

    if "courier" in query:
        return "Do you need orders assigned to a courier, their route, or recent deliveries?"

    if "route" in query:
        return "Do you want an order route, a courier route, or a route between hubs?"

    if "delivery" in query:
        return "Do you want recent deliveries, delivery schedules, or order details?"

    return ClarificationManager.intent_question()


def classify_domain_task(
    user_query: str,
    entities: dict[str, str] | None = None,
    domain: str = "logistics",
) -> dict[str, Any]:
    """
    Classify the logistics *task*. Domain is owned by coarse authorization.

    Domain classification is never performed here: coarse authorization is the
    single domain owner, and only logistics queries reach this function
    (inventory bypasses to NL-SQL). The provided ``domain`` is trusted.

    Routing order:
      1. Entity extraction (provided by caller)
      2. Candidate intent narrowing
      3. LLM task classification
      4. Keyword fallback only when LLM fails
    """
    resolved_entities = dict(entities or {})
    # Hard domain pin: intent never infers or overwrites the domain. Only
    # logistics reaches this node, so the domain is always logistics regardless
    # of the classifier output. ``domain`` is accepted for call-site clarity but
    # can never flip the turn to inventory.
    domain = _LOGISTICS_DOMAIN
    routing_query = _normalize_logistics_abbreviations(user_query)

    candidate_tasks = narrow_candidate_tasks(resolved_entities, domain=domain)

    llm_result = _classify_with_llm(user_query, resolved_entities, candidate_tasks)
    if llm_result:
        return {
            **llm_result,
            "domain": domain,
            "source": "llm_intent_classifier",
            "candidate_tasks": candidate_tasks,
        }

    fallback = _keyword_fallback_task(
        routing_query,
        candidate_tasks=candidate_tasks,
        domain=domain,
    )
    return {
        **fallback,
        "domain": domain,
        "source": "keyword_fallback",
        "candidate_tasks": candidate_tasks,
    }
