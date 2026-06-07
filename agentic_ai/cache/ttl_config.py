"""Central TTL and cacheability configuration."""

from __future__ import annotations

CACHEABLE_TASKS: frozenset[str] = frozenset({
    "inventory_nlsql",
    "shipment_lookup",
    "courier_lookup",
    "eta_lookup",
    "demand_forecast",
})

TASK_TTL_SECONDS: dict[str, int] = {
    "inventory_nlsql": 300,
    "shipment_lookup": 120,
    "courier_lookup": 300,
    "eta_lookup": 120,
    "demand_forecast": 3600,
}


def is_cacheable(task: str) -> bool:
    """Return True when the task supports caching."""
    return task in CACHEABLE_TASKS


def ttl_for_task(task: str) -> int | None:
    """Return TTL seconds for a cacheable task, or None if not cacheable."""
    return TASK_TTL_SECONDS.get(task)
