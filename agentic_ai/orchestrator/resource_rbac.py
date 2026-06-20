"""Centralized resource-level authorization.

This is the single place where role boundaries and COURIER resource ownership
are enforced (Phase 2). ADMIN and LOGISTICS/INVENTORY behavior is unchanged;
only COURIER requests get ownership checks based on ``state["bound_courier_id"]``
(produced by Phase 1 identity binding in entity resolution).

Authorization is NOT spread across nodes: entity resolution resolves identities,
this module enforces access.
"""

from __future__ import annotations

import re
from typing import Any

from integrations.aura_bridge import fetch_order_route
from orchestrator.hitl_session import get_active_hitl_session
from orchestrator.state import AgentState
from orchestrator.task_registry import DYNAMIC_GRAPH_QUERY, is_task_allowed
from orchestrator.tracing import log_authz_allow, log_authz_deny, log_authz_deny_order

# Authorization outcomes. ALLOW/DENY behave exactly as the previous boolean
# result (allowed True/False). DEFER means ownership cannot yet be evaluated
# because scope context is missing: the turn continues to parameter_preparation,
# which collects the missing scope via HITL, and authorize re-evaluates on the
# resume pass. No deterministic task ever returns DEFER.
AUTHZ_ALLOW = "ALLOW"
AUTHZ_DENY = "DENY"
AUTHZ_DEFER = "DEFER"

# Session marker persisted by parameter_preparation when it asks the courier to
# confirm a self-scoped dynamic query. On the affirmative resume, this module
# binds courier_id == bound_courier_id and returns ALLOW.
DEFER_SELF_SCOPE_REASON = "self_scope_confirmation"

# Entity keys that indicate a hub reference (couriers can never query hubs).
_HUB_SCOPE_KEYS: tuple[str, ...] = (
    "hub_id",
    "hub_name",
    "from_hub",
    "to_hub",
    "from_hub_id",
    "to_hub_id",
)

_AFFIRMATIVE_TOKENS: frozenset[str] = frozenset({
    "yes", "y", "yeah", "yep", "yup", "sure", "ok", "okay",
    "correct", "right", "my", "mine", "own", "please", "confirm", "confirmed",
})

_NEGATIVE_TOKENS: frozenset[str] = frozenset({
    "no", "not", "dont", "nope", "never", "cancel",
})

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
) -> tuple[str, str | None, dict[str, str], dict[str, Any] | None]:
    """
    Authorize after intent classification and entity resolution.

    Order: role present -> ADMIN bypass -> COURIER resource authorization ->
    LOGISTICS/INVENTORY task-level RBAC.

    Returns (status, reason, entities, prefetched_order_route) where status is
    one of AUTHZ_ALLOW / AUTHZ_DENY / AUTHZ_DEFER. Deterministic tasks only ever
    return ALLOW or DENY (identical to the previous boolean behavior).
    """
    role = state.get("user_role")
    task = state.get("task", "")
    entities = dict(state.get("entities") or {})

    if not role:
        return AUTHZ_DENY, "User identity not provided", entities, None

    # Rule 5: ADMIN retains unrestricted behavior.
    if role == "ADMIN":
        return AUTHZ_ALLOW, None, entities, None

    # COURIER: centralized resource ownership authorization (Rules 1-4, 6).
    if role == "COURIER":
        return _authorize_courier(state, task, entities)

    # Rule 5: LOGISTICS / INVENTORY retain current behavior (task-level RBAC only).
    if not is_task_allowed(role, task):
        return AUTHZ_DENY, f"Role {role} is not allowed to execute {task}", entities, None

    return AUTHZ_ALLOW, None, entities, None


def _authorize_courier(
    state: AgentState,
    task: str,
    entities: dict[str, str],
) -> tuple[str, str | None, dict[str, str], dict[str, Any] | None]:
    """Enforce COURIER resource ownership for a single request."""
    trace_id = state.get("trace_id") or "unknown"
    bound_courier_id = (str(state.get("bound_courier_id") or "")).strip() or None

    # Dynamic GraphDB fallback: scope-based ALLOW / DENY / DEFER.
    if task == DYNAMIC_GRAPH_QUERY:
        return _authorize_courier_dynamic(state, entities, bound_courier_id, trace_id)

    # Rule 4: hub information is never available to couriers.
    if task in COURIER_DENIED_HUB_TASKS:
        log_authz_deny(
            trace_id,
            task=task,
            bound_courier_id=bound_courier_id,
            requested_courier_id=None,
        )
        return AUTHZ_DENY, _HUB_DENIED_MESSAGE, entities, None

    # Task-level RBAC (unchanged): a courier may only run its permitted tasks.
    if not is_task_allowed("COURIER", task):
        return AUTHZ_DENY, f"Role COURIER is not allowed to execute {task}", entities, None

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
            return AUTHZ_DENY, message, entities, None

    log_authz_allow(trace_id, task=task, bound_courier_id=bound_courier_id)
    return AUTHZ_ALLOW, None, entities, None


def _authorize_courier_dynamic(
    state: AgentState,
    entities: dict[str, str],
    bound_courier_id: str | None,
    trace_id: str,
) -> tuple[str, str | None, dict[str, str], dict[str, Any] | None]:
    """Scope-based authorization for a courier's dynamic GraphDB query.

    Decision by available scope:
      - hub reference present       -> DENY (hubs are never courier-visible)
      - order_id present            -> ownership check (ALLOW/DENY)
      - courier_id present          -> must equal bound_courier_id (ALLOW/DENY)
      - self_scoped                 -> ALLOW (bound courier)
      - no scope, confirmed self    -> bind courier_id = bound, ALLOW
      - no scope, not confirmed     -> DEFER (parameter_preparation will ask)
    """
    # Rule 4: hubs are never available to couriers (sufficient info to deny).
    if any((entities.get(key) or "").strip() for key in _HUB_SCOPE_KEYS):
        log_authz_deny(
            trace_id,
            task=DYNAMIC_GRAPH_QUERY,
            bound_courier_id=bound_courier_id,
            requested_courier_id=None,
        )
        return AUTHZ_DENY, _HUB_DENIED_MESSAGE, entities, None

    # Rule 3: order ownership verified against the order's assignment.
    order_id = (entities.get("order_id") or "").strip()
    if order_id:
        return _authorize_courier_order(DYNAMIC_GRAPH_QUERY, entities, bound_courier_id, trace_id)

    # Explicit courier reference must match the bound identity.
    requested = (entities.get("courier_id") or "").strip()
    if requested:
        if bound_courier_id and requested == bound_courier_id:
            log_authz_allow(trace_id, task=DYNAMIC_GRAPH_QUERY, bound_courier_id=bound_courier_id)
            return AUTHZ_ALLOW, None, entities, None
        log_authz_deny(
            trace_id,
            task=DYNAMIC_GRAPH_QUERY,
            bound_courier_id=bound_courier_id,
            requested_courier_id=requested,
        )
        return AUTHZ_DENY, _ROUTE_DENIED_MESSAGE, entities, None

    # Self-scoped: entity resolution already binds courier_id == bound, but guard
    # in case the binding is absent.
    if (entities.get("self_scoped") or "").strip().lower() == "true":
        if bound_courier_id:
            entities["courier_id"] = bound_courier_id
        log_authz_allow(trace_id, task=DYNAMIC_GRAPH_QUERY, bound_courier_id=bound_courier_id)
        return AUTHZ_ALLOW, None, entities, None

    # No scope yet. If the courier just affirmatively confirmed a self-scoped
    # dynamic query in an active clarification, bind to the bound courier and
    # allow; otherwise defer so parameter_preparation can ask.
    if bound_courier_id and _self_scope_confirmed(state):
        entities["courier_id"] = bound_courier_id
        entities["self_scoped"] = "true"
        log_authz_allow(trace_id, task=DYNAMIC_GRAPH_QUERY, bound_courier_id=bound_courier_id)
        return AUTHZ_ALLOW, None, entities, None

    return AUTHZ_DEFER, "self_scope_required", entities, None


def _self_scope_confirmed(state: AgentState) -> bool:
    """Return True when an active self-scope clarification was answered affirmatively."""
    session = get_active_hitl_session(state)
    if not session or session.get("defer_reason") != DEFER_SELF_SCOPE_REASON:
        return False

    original = (session.get("original_query") or "").strip()
    full = (state.get("user_query") or "").strip()
    if original and full.lower().startswith(original.lower()):
        answer = full[len(original):].strip()
    else:
        answer = full
    return _is_affirmative(answer)


def _is_affirmative(text: str) -> bool:
    """Best-effort affirmative detection for a self-scope confirmation answer."""
    tokens = set(re.findall(r"\b\w+\b", text.lower()))
    if tokens & _NEGATIVE_TOKENS:
        return False
    return bool(tokens & _AFFIRMATIVE_TOKENS)


def _authorize_courier_order(
    task: str,
    entities: dict[str, str],
    bound_courier_id: str | None,
    trace_id: str,
) -> tuple[str, str | None, dict[str, str], dict[str, Any] | None]:
    """Rule 3: verify the requested order is assigned to the bound courier."""
    order_id = (entities.get("order_id") or "").strip()

    # No specific order requested; nothing to ownership-check here. Parameter
    # preparation will request the order id (existing behavior).
    if not order_id:
        log_authz_allow(trace_id, task=task, bound_courier_id=bound_courier_id)
        return AUTHZ_ALLOW, None, entities, None

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
        return AUTHZ_ALLOW, None, entities, order_route

    log_authz_deny_order(
        trace_id,
        order_id=order_id,
        assigned_courier_id=assigned_courier_id,
        bound_courier_id=bound_courier_id,
    )
    return AUTHZ_DENY, _ORDER_LOOKUP_DENIED_MESSAGE, entities, None
