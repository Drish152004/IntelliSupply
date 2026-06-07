"""Central role-to-task permission matrix."""

from __future__ import annotations

ALL_TASKS: frozenset[str] = frozenset({
    "inventory_nlsql",
    "shipment_lookup",
    "courier_lookup",
    "eta_lookup",
    "eta_prediction",
    "route_lookup",
    "route_prediction",
    "next_stop_prediction",
    "demand_forecast",
})

LOGISTICS_TASKS: frozenset[str] = frozenset({
    "shipment_lookup",
    "courier_lookup",
    "eta_lookup",
    "eta_prediction",
    "route_lookup",
    "route_prediction",
    "next_stop_prediction",
    "demand_forecast",
})

COURIER_TASKS: frozenset[str] = frozenset({
    "route_lookup",
    "route_prediction",
    "next_stop_prediction",
})

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "ADMIN": ALL_TASKS,
    "LOGISTICS": LOGISTICS_TASKS,
    "INVENTORY": frozenset({"inventory_nlsql"}),
    "COURIER": COURIER_TASKS,
}

VALID_ROLES: frozenset[str] = frozenset(ROLE_PERMISSIONS)
