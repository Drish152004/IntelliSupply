"""
Single source of truth for domains, tasks, keywords, RBAC, and cache TTL.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# --- Domains ---

VALID_DOMAINS: frozenset[str] = frozenset({"inventory", "logistics"})

INVENTORY_TASKS: frozenset[str] = frozenset({"inventory_nlsql"})

LOGISTICS_RETRIEVAL_TASKS: frozenset[str] = frozenset({
    "shipment_lookup",
    "courier_lookup",
    "eta_lookup",
    "route_lookup",
    "next_stop_lookup",
    "courier_route_lookup",
    "hub_lookup",
    "city_lookup",
})

# Reserved for future ML orchestrator wiring (LOGISTICS / ADMIN may execute when implemented).
FUTURE_LOGISTICS_ML_TASKS: frozenset[str] = frozenset({
    "eta_prediction",
    "route_prediction",
    "next_stop_prediction",
    "demand_forecast",
})

LOGISTICS_TASKS: frozenset[str] = LOGISTICS_RETRIEVAL_TASKS | FUTURE_LOGISTICS_ML_TASKS

VALID_TASKS: frozenset[str] = INVENTORY_TASKS | LOGISTICS_RETRIEVAL_TASKS

DOMAIN_TASK_MAP: dict[str, frozenset[str]] = {
    "inventory": INVENTORY_TASKS,
    "logistics": LOGISTICS_RETRIEVAL_TASKS,
}

# --- Keywords (coarse domain detection + intent fallback) ---

INVENTORY_SINGLE_WORD_KEYWORDS: tuple[str, ...] = (
    "inventory",
    "stock",
    "stocks",
    "product",
    "products",
    "quantity",
    "available",
    "availability",
    "warehouse",
    "units",
    "reorder",
    "item",
    "items",
    "catalog",
    "sku",
    "skus",
    "amount",
    "electronics",
    "electronic",
    "clothing",
    "furniture",
    "toy",
    "toys",
    "grocery",
    "groceries",
)

INVENTORY_PHRASE_KEYWORDS: tuple[str, ...] = (
    "low stock",
    "out of stock",
)

LOGISTICS_SINGLE_WORD_KEYWORDS: tuple[str, ...] = (
    "shipment",
    "shipments",
    "order",
    "orders",
    "package",
    "packages",
    "delivery",
    "deliveries",
    "route",
    "eta",
    "tracking",
    "track",
    "courier",
    "dispatch",
)

LOGISTICS_PHRASE_KEYWORDS: tuple[str, ...] = (
    "next stop",
    "where is",
)

INVENTORY_KEYWORDS: tuple[str, ...] = INVENTORY_SINGLE_WORD_KEYWORDS + INVENTORY_PHRASE_KEYWORDS

LOGISTICS_KEYWORDS: tuple[str, ...] = LOGISTICS_SINGLE_WORD_KEYWORDS + LOGISTICS_PHRASE_KEYWORDS

# --- Role permissions (task-level, enforced after intent) ---

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "ADMIN": INVENTORY_TASKS | LOGISTICS_TASKS,
    "LOGISTICS": LOGISTICS_TASKS,
    "INVENTORY": INVENTORY_TASKS,
    "COURIER": frozenset({
        "route_lookup",
        "courier_lookup",
        "shipment_lookup",
        "eta_lookup",
        "next_stop_lookup",
        "courier_route_lookup",
    }),
}

VALID_ROLES: frozenset[str] = frozenset(ROLE_PERMISSIONS)

COURIER_SELF_SCOPED_TASKS: frozenset[str] = frozenset({
    "courier_lookup",
    "route_lookup",
    "shipment_lookup",
    "eta_lookup",
    "next_stop_lookup",
    "courier_route_lookup",
})

COURIER_RESOURCE_SCOPED_TASKS: frozenset[str] = COURIER_SELF_SCOPED_TASKS

# --- Clarification ---

CONFIDENCE_THRESHOLD = 0.70
EXTREME_LOW_CONFIDENCE_THRESHOLD = 0.30

TASKS_BYPASS_INTENT_CLARIFICATION: frozenset[str] = frozenset({
    "inventory_nlsql",
    "city_lookup",
})

# --- Entity requirements (logistics lookups) ---

QUERY_ENTITY_REQUIREMENTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "shipment_lookup": (("order_id",), ("shipment_id",), ("courier_id",), ("self_scoped",)),
    "courier_lookup": (("courier_id",), ("self_scoped",)),
    "eta_lookup": (("order_id",), ("shipment_id",), ("self_scoped",), ("courier_id",)),
    "route_lookup": (("order_id",), ("from_hub", "to_hub"), ("self_scoped",), ("courier_id",)),
    "next_stop_lookup": (
        ("courier_id", "current_stop"),
        ("courier_id", "last_completed_order"),
        ("self_scoped", "current_stop"),
        ("self_scoped", "last_completed_order"),
    ),
    "courier_route_lookup": (("courier_id",), ("self_scoped",)),
    "hub_lookup": ((), ("city_name",)),
    "city_lookup": ((),),
}

# --- Cache TTL (seconds) ---

CACHE_TTL_BY_TASK: dict[str, int] = {
    "inventory_nlsql": 300,
    "shipment_lookup": 120,
    "courier_lookup": 120,
    "eta_lookup": 120,
    "route_lookup": 120,
    "next_stop_lookup": 120,
    "courier_route_lookup": 120,
    "hub_lookup": 300,
    "city_lookup": 300,
}

CACHEABLE_TASKS: frozenset[str] = frozenset(CACHE_TTL_BY_TASK)


def ttl_for_task(task: str) -> int | None:
    return CACHE_TTL_BY_TASK.get(task)


def is_task_allowed(role: str, task: str) -> bool:
    if role == "ADMIN":
        return True
    allowed = ROLE_PERMISSIONS.get(role, frozenset())
    if task in allowed:
        return True
    return task in FUTURE_LOGISTICS_ML_TASKS and role in {"ADMIN", "LOGISTICS"}


def _normalize_query_text(query: str) -> str:
    """Lowercase and normalize punctuation before tokenization or phrase matching."""
    normalized = query.lower().replace(";", "")
    for separator in (",", ".", "/", "-"):
        normalized = normalized.replace(separator, " ")
    return normalized


def tokenize_query(query: str) -> set[str]:
    """Return lowercased word tokens from a query."""
    normalized = _normalize_query_text(query)
    return set(re.findall(r"\b\w+\b", normalized))


def _match_domain_keywords(
    *,
    tokens: set[str],
    normalized_query: str,
    single_words: tuple[str, ...],
    phrases: tuple[str, ...],
) -> list[str]:
    matched: list[str] = []
    for keyword in single_words:
        if keyword in tokens:
            matched.append(keyword)
    for phrase in phrases:
        if phrase in normalized_query:
            matched.append(phrase)
    return matched


def match_coarse_domain_keywords(query: str) -> tuple[list[str], list[str]]:
    """Return matched inventory and logistics keywords for a query."""
    normalized_query = _normalize_query_text(query)
    tokens = tokenize_query(query)
    matched_inventory = _match_domain_keywords(
        tokens=tokens,
        normalized_query=normalized_query,
        single_words=INVENTORY_SINGLE_WORD_KEYWORDS,
        phrases=INVENTORY_PHRASE_KEYWORDS,
    )
    matched_logistics = _match_domain_keywords(
        tokens=tokens,
        normalized_query=normalized_query,
        single_words=LOGISTICS_SINGLE_WORD_KEYWORDS,
        phrases=LOGISTICS_PHRASE_KEYWORDS,
    )
    logger.info(
        "keyword_match inventory=%s logistics=%s query=%r",
        matched_inventory,
        matched_logistics,
        query,
    )
    return matched_inventory, matched_logistics


def coarse_domain_from_matches(
    matched_inventory: list[str],
    matched_logistics: list[str],
) -> str | None:
    """Resolve domain from matched keyword lists."""
    inventory_score = len(matched_inventory)
    logistics_score = len(matched_logistics)

    if inventory_score > 0 and logistics_score == 0:
        return "inventory"
    if logistics_score > 0 and inventory_score == 0:
        return "logistics"
    return None


def detect_coarse_domain(query: str) -> str | None:
    """
    Return coarse domain from token-aware keyword matching.

    Returns "inventory", "logistics", or None when ambiguous
    (no keywords, or keywords from both domains).
    """
    matched_inventory, matched_logistics = match_coarse_domain_keywords(query)
    return coarse_domain_from_matches(matched_inventory, matched_logistics)
