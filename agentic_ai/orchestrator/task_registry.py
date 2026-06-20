"""
Single source of truth for domains, tasks, keywords, and RBAC.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# --- Domains ---

VALID_DOMAINS: frozenset[str] = frozenset({"inventory", "logistics"})

INVENTORY_TASKS: frozenset[str] = frozenset({"inventory_nlsql"})

LOGISTICS_RETRIEVAL_TASKS: frozenset[str] = frozenset({
    "order_lookup",
    "courier_orders",
    "courier_route",
    "recent_routes",
    "delivery_days",
    "hub_route",
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
    "city",
    "cities",
    "hubs",
    "hub"
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
        "order_lookup",
        "courier_orders",
        "courier_route",
        "recent_routes",
    }),
}

VALID_ROLES: frozenset[str] = frozenset(ROLE_PERMISSIONS)

COURIER_SELF_SCOPED_TASKS: frozenset[str] = frozenset({
    "order_lookup",
    "courier_orders",
    "courier_route",
})

# Tasks where a COURIER must be confined to their own data. recent_routes is
# resource-scoped (not self-only phrasing) so couriers cannot list other
# couriers' deliveries.
COURIER_RESOURCE_SCOPED_TASKS: frozenset[str] = COURIER_SELF_SCOPED_TASKS | frozenset({
    "recent_routes",
})

# --- Clarification ---

CONFIDENCE_THRESHOLD = 0.70
EXTREME_LOW_CONFIDENCE_THRESHOLD = 0.30

TASKS_BYPASS_INTENT_CLARIFICATION: frozenset[str] = frozenset({
    "inventory_nlsql",
})


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
