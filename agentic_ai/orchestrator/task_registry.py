"""
Single source of truth for domains, tasks, keywords, RBAC, and cache TTL.
"""

from __future__ import annotations

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

# --- Keywords (routing hints + intent fallback) ---

INVENTORY_KEYWORDS: tuple[str, ...] = (
    "stock",
    "inventory",
    "warehouse",
    "product",
    "available",
    "laptop",
    "laptops",
    "iphone",
    "iphones",
    "how many",
    "sku",
    "units",
)

LOGISTICS_KEYWORDS: tuple[str, ...] = (
    "shipment",
    "route",
    "delivery",
    "eta",
    "transport",
    "courier",
    "order",
    "tracking",
    "dispatch",
    "next stop",
    "hub",
    "city",
)

AMBIGUOUS_KEYWORDS: frozenset[str] = frozenset({"hub"})

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
    "shipment_lookup",
    "courier_lookup",
    "eta_lookup",
    "route_lookup",
    "next_stop_lookup",
    "courier_route_lookup",
    "hub_lookup",
    "city_lookup",
})

# --- Entity requirements (logistics lookups) ---

QUERY_ENTITY_REQUIREMENTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "shipment_lookup": (("order_id",), ("shipment_id",), ("courier_id",), ("self_scoped",)),
    "courier_lookup": (("courier_id",), ("self_scoped",)),
    "eta_lookup": (("order_id",), ("shipment_id",), ("self_scoped",), ("courier_id",)),
    "route_lookup": (("order_id",), ("from_hub", "to_hub"), ("self_scoped",), ("courier_id",)),
    "next_stop_lookup": (("courier_id",), ("self_scoped",)),
    "courier_route_lookup": (("courier_id",), ("self_scoped",)),
    "hub_lookup": (("city_name",), ("hub_id",), ()),
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

SELF_SCOPED_PHRASES: tuple[tuple[str, str], ...] = (
    ("my route", "courier_route_lookup"),
    ("my shipments", "shipment_lookup"),
    ("my shipment", "shipment_lookup"),
    ("my eta", "eta_lookup"),
    ("my next stop", "next_stop_lookup"),
    ("next stop", "next_stop_lookup"),
)


def ttl_for_task(task: str) -> int | None:
    return CACHE_TTL_BY_TASK.get(task)


def is_task_allowed(role: str, task: str) -> bool:
    if role == "ADMIN":
        return True
    allowed = ROLE_PERMISSIONS.get(role, frozenset())
    if task in allowed:
        return True
    return task in FUTURE_LOGISTICS_ML_TASKS and role in {"ADMIN", "LOGISTICS"}


def score_domain_keywords(query: str) -> dict[str, int]:
    q = query.lower()
    inventory = sum(1 for kw in INVENTORY_KEYWORDS if kw in q)
    logistics = sum(1 for kw in LOGISTICS_KEYWORDS if kw in q)
    if any(kw in q for kw in AMBIGUOUS_KEYWORDS):
        inventory += 1
        logistics += 1
    return {"inventory": inventory, "logistics": logistics}


def detect_coarse_domain(query: str) -> tuple[str | None, float, bool]:
    """Return (likely_domain, confidence, is_ambiguous) for routing/cache hints only."""
    scores = score_domain_keywords(query)
    inv, log = scores["inventory"], scores["logistics"]

    if inv == 0 and log == 0:
        return None, 0.0, True

    if inv > 0 and log > 0 and abs(inv - log) <= 1:
        return None, 0.4, True

    if inv > log:
        return "inventory", min(0.95, 0.6 + inv * 0.1), False
    if log > inv:
        return "logistics", min(0.95, 0.6 + log * 0.1), False

    return None, 0.4, True
