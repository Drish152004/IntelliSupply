"""
Entity-driven intent narrowing for the orchestration layer.

Domain ownership belongs entirely to coarse authorization. Only logistics
queries reach intent (inventory bypasses to NL-SQL), so this module never
infers or re-classifies the domain — it only narrows the logistics *task*
search space using extracted entities.

Routing pipeline:
  1. Entity extraction (upstream, logistics only)
  2. Candidate intent narrowing (this module)
  3. LLM task classification (intent_task_classifier)
  4. Clarification on low confidence (intent node)
"""

from __future__ import annotations

import logging

from context.entity_extractor import has_courier_entity
from orchestrator.task_registry import INVENTORY_TASKS

logger = logging.getLogger(__name__)

_DEFAULT_LOGISTICS_CANDIDATES: list[str] = [
    "order_lookup",
    "courier_orders",
    "courier_route",
    "recent_routes",
    "delivery_days",
    "hub_route",
]

_COURIER_CANDIDATES: list[str] = [
    "courier_orders",
    "courier_route",
    "recent_routes",
]


def _has_hub_pair(entities: dict[str, str]) -> bool:
    if entities.get("from_hub") and entities.get("to_hub"):
        return True
    return bool(
        entities.get("to_hub")
        and (entities.get("from_hub") or entities.get("hub_id"))
    )


def narrow_candidate_tasks(
    entities: dict[str, str],
    *,
    domain: str = "logistics",
) -> list[str]:
    """
    Return logistics candidate tasks narrowed by extracted entities.

    Entities reduce the search space; they never select the final task. Only
    logistics reaches intent, so there is no inventory branch here.
    """
    if entities.get("order_id"):
        return ["order_lookup"]

    if _has_hub_pair(entities):
        return ["hub_route"]

    if has_courier_entity(entities) or entities.get("self_scoped") == "true":
        return list(_COURIER_CANDIDATES)

    result = list(_DEFAULT_LOGISTICS_CANDIDATES)
    logger.info(
        "intent_candidates entity_keys=%s candidates=%s",
        sorted(entities.keys()),
        result,
    )
    return result


def domain_for_task(task: str) -> str:
    if task in INVENTORY_TASKS:
        return "inventory"
    return "logistics"
