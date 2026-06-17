"""
Entity-driven intent narrowing for the orchestration layer.

Routing pipeline:
  1. Entity extraction (upstream)
  2. Candidate intent narrowing (this module)
  3. LLM task classification (intent_task_classifier)
  4. Clarification on low confidence (intent node)
"""

from __future__ import annotations

import logging

from context.entity_extractor import has_courier_entity
from orchestrator.task_registry import INVENTORY_TASKS, VALID_DOMAINS

logger = logging.getLogger(__name__)

_INVENTORY_ENTITY_KEYS: frozenset[str] = frozenset({
    "sku_id",
    "warehouse_id",
    "product_name",
})

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


def _has_inventory_entities(entities: dict[str, str]) -> bool:
    return any(entities.get(key) for key in _INVENTORY_ENTITY_KEYS)


def infer_domain(
    *,
    entities: dict[str, str],
    domain_hint: str | None,
    inventory_keyword_score: int,
    logistics_keyword_score: int,
) -> str:
    """Infer coarse domain without assigning a logistics task."""
    if _has_inventory_entities(entities):
        if domain_hint == "logistics" and logistics_keyword_score > inventory_keyword_score:
            return "logistics"
        return "inventory"

    if domain_hint in VALID_DOMAINS:
        if domain_hint == "inventory" and inventory_keyword_score >= logistics_keyword_score:
            return "inventory"
        if domain_hint == "logistics" and logistics_keyword_score >= inventory_keyword_score:
            return "logistics"

    if inventory_keyword_score > 0 and logistics_keyword_score == 0:
        return "inventory"
    if logistics_keyword_score > 0 and inventory_keyword_score == 0:
        return "logistics"
    if inventory_keyword_score > logistics_keyword_score:
        return "inventory"
    if logistics_keyword_score > inventory_keyword_score:
        return "logistics"

    return domain_hint if domain_hint in VALID_DOMAINS else "logistics"


def narrow_candidate_tasks(
    entities: dict[str, str],
    *,
    domain: str,
) -> list[str]:
    """
    Return candidate tasks narrowed by extracted entities.

    Entities reduce the search space; they never select the final task.
    """
    if domain == "inventory":
        return sorted(INVENTORY_TASKS)

    if entities.get("order_id") or entities.get("shipment_id"):
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
