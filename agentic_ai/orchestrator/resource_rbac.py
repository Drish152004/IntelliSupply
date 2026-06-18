"""Centralized resource-level authorization.

This is the single place where role boundaries and COURIER resource ownership
are enforced (Phase 2). ADMIN and LOGISTICS/INVENTORY behavior is unchanged;
only COURIER requests get ownership checks based on ``state["bound_courier_id"]``
(produced by Phase 1 identity binding in entity resolution).

Authorization is NOT spread across nodes: entity resolution resolves identities,
this module enforces access.
"""

from __future__ import annotations

from typing import Any

from integrations.aura_bridge import fetch_order_route
from orchestrator.state import AgentState
from orchestrator.task_registry import is_task_allowed
from orchestrator.tracing import log_authz_allow, log_authz_deny, log_authz_deny_order

# Rule 4: tasks that expose hub information are never available to couriers.
COURIER_DENIED_HUB_TASKS: frozenset[str] = frozenset({
    "hub_route",
    "delivery_days",
})

# Rule 3: order ownership is verified by order_id (assigned_courier_id), not courier_id.
COURIER_ORDER_OWNERSHIP_TASKS: frozenset[str] = frozenset({
    "order_lookup",
})

# Rules 1 & 2: route / orders ownership verified by comparing the requested
# courier_id against the bound courier identity.
COURIER_ORDERS_OWNERSHIP_TASKS: frozenset[str] = frozenset({
    "courier_orders",
})
COURIER_ROUTE_OWNERSHIP_TASKS: frozenset[str] = frozenset({
    "courier_route",
    "recent_routes",
})

_ROUTE_DENIED_MESSAGE = "Sorry, you can only access your own route."
_ORDERS_DENIED_MESSAGE = "Sorry, you can only access your own assigned orders."
_ORDER_LOOKUP_DENIED_MESSAGE = (
    "Sorry, you cannot access information for orders that are not assigned to you."
)
_HUB_DENIED_MESSAGE = (
    "Sorry, hub information is only available to logistics and admin users."
)


def authorize_task_and_resources(
    state: AgentState,
) -> tuple[bool, str | None, dict[str, str], dict[str, Any] | None]:
    """
    Authorize after intent classification and entity resolution.

    Order: role present -> ADMIN bypass -> COURIER resource authorization ->
    LOGISTICS/INVENTORY task-level RBAC.

    Returns (allowed, reason, entities, prefetched_order_route).
    """
    role = state.get("user_role")
    task = state.get("task", "")
    entities = dict(state.get("entities") or {})

    if not role:
        return False, "User identity not provided", entities, None

    # Rule 5: ADMIN retains unrestricted behavior.
    if role == "ADMIN":
        return True, None, entities, None

    # COURIER: centralized resource ownership authorization (Rules 1-4, 6).
    if role == "COURIER":
        return _authorize_courier(state, task, entities)

    # Rule 5: LOGISTICS / INVENTORY retain current behavior (task-level RBAC only).
    if not is_task_allowed(role, task):
        return False, f"Role {role} is not allowed to execute {task}", entities, None

    return True, None, entities, None


def _authorize_courier(
    state: AgentState,
    task: str,
    entities: dict[str, str],
) -> tuple[bool, str | None, dict[str, str], dict[str, Any] | None]:
    """Enforce COURIER resource ownership for a single request."""
    trace_id = state.get("trace_id") or "unknown"
    bound_courier_id = (str(state.get("bound_courier_id") or "")).strip() or None

    # Rule 4: hub information is never available to couriers.
    if task in COURIER_DENIED_HUB_TASKS:
        log_authz_deny(
            trace_id,
            task=task,
            bound_courier_id=bound_courier_id,
            requested_courier_id=None,
        )
        return False, _HUB_DENIED_MESSAGE, entities, None

    # Task-level RBAC (unchanged): a courier may only run its permitted tasks.
    if not is_task_allowed("COURIER", task):
        return False, f"Role COURIER is not allowed to execute {task}", entities, None

    # Rule 3: order lookup ownership is verified against the order's assignment.
    if task in COURIER_ORDER_OWNERSHIP_TASKS:
        return _authorize_courier_order(task, entities, bound_courier_id, trace_id)

    # Rules 1 & 2 (and recent_routes): a courier may only target their own
    # courier_id. Self-scoped queries already inject courier_id == bound_courier_id
    # (Phase 1), so they pass without clarification. Only an explicit mismatch is
    # denied; a missing courier_id is left for parameter preparation to handle.
    if task in COURIER_ROUTE_OWNERSHIP_TASKS or task in COURIER_ORDERS_OWNERSHIP_TASKS:
        requested = (entities.get("courier_id") or "").strip()
        if requested and requested != (bound_courier_id or ""):
            log_authz_deny(
                trace_id,
                task=task,
                bound_courier_id=bound_courier_id,
                requested_courier_id=requested,
            )
            message = (
                _ORDERS_DENIED_MESSAGE
                if task in COURIER_ORDERS_OWNERSHIP_TASKS
                else _ROUTE_DENIED_MESSAGE
            )
            return False, message, entities, None

    log_authz_allow(trace_id, task=task, bound_courier_id=bound_courier_id)
    return True, None, entities, None


def _authorize_courier_order(
    task: str,
    entities: dict[str, str],
    bound_courier_id: str | None,
    trace_id: str,
) -> tuple[bool, str | None, dict[str, str], dict[str, Any] | None]:
    """Rule 3: verify the requested order is assigned to the bound courier."""
    order_id = (entities.get("order_id") or "").strip()

    # No specific order requested; nothing to ownership-check here. Parameter
    # preparation will request the order id (existing behavior).
    if not order_id:
        log_authz_allow(trace_id, task=task, bound_courier_id=bound_courier_id)
        return True, None, entities, None

    order_route = fetch_order_route(order_id)
    assigned_courier_id = (
        str((order_route or {}).get("assigned_courier_id") or "")
    ).strip() or None

    # Ownership is by order assignment; drop any stray courier_id from the payload.
    entities.pop("courier_id", None)

    if (
        assigned_courier_id
        and bound_courier_id
        and assigned_courier_id == bound_courier_id
    ):
        log_authz_allow(trace_id, task=task, bound_courier_id=bound_courier_id)
        # Pass the already-fetched route downstream to avoid a second lookup.
        return True, None, entities, order_route

    log_authz_deny_order(
        trace_id,
        order_id=order_id,
        assigned_courier_id=assigned_courier_id,
        bound_courier_id=bound_courier_id,
    )
    return False, _ORDER_LOOKUP_DENIED_MESSAGE, entities, None
