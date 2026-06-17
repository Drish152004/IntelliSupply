"""Resource-level authorization: courier ownership and role boundaries."""

from __future__ import annotations

from typing import Any

from integrations.aura_bridge import fetch_order_route
from orchestrator.task_registry import COURIER_RESOURCE_SCOPED_TASKS, is_task_allowed
from orchestrator.state import AgentState

COURIER_ORDER_OWNERSHIP_TASKS: frozenset[str] = frozenset({
    "shipment_lookup",
    "route_lookup",
    "eta_lookup",
})


def authorize_task_and_resources(
    state: AgentState,
) -> tuple[bool, str | None, dict[str, str], dict[str, Any] | None]:
    """
    Authorize after intent classification and entity extraction.

    Order: role present -> task allowed for role -> domain boundary -> courier resource scope
    -> courier order ownership (order_id tasks).
    Consumes state["entities"] as produced by entity extraction; does not infer self_scoped.
    """
    role = state.get("user_role")
    task = state.get("task", "")

    entities = dict(state.get("entities") or {})
    prefetched_order_route: dict[str, Any] | None = None

    if not role:
        return False, "User identity not provided", entities, None

    if role == "ADMIN":
        return True, None, entities, None

    if not is_task_allowed(role, task):
        return False, f"Role {role} is not allowed to execute {task}", entities, None

    if role != "COURIER" or task not in COURIER_RESOURCE_SCOPED_TASKS:
        return True, None, entities, None

    session = state.get("logistics_session") or {}
    bound_courier = session.get("courier_id")
    if not bound_courier:
        return False, "Courier identity is not bound to this session", entities, None

    requested = entities.get("courier_id")
    if requested and str(requested) != str(bound_courier):
        return (
            False,
            f"You are not authorized to access courier {requested}'s data",
            entities,
            None,
        )

    order_id = entities.get("order_id")
    if task in COURIER_ORDER_OWNERSHIP_TASKS and order_id:
        entities.pop("courier_id", None)
        order_route = fetch_order_route(order_id)
        assigned_courier_id = (order_route or {}).get("assigned_courier_id")
        if not assigned_courier_id or str(assigned_courier_id) != str(bound_courier):
            return (
                False,
                f"Order {order_id} is not assigned to you",
                entities,
                None,
            )
        prefetched_order_route = order_route

    if task in {"courier_lookup", "next_stop_lookup", "courier_route_lookup", "shipment_lookup"}:
        if (
            entities.get("self_scoped") == "true"
            and not requested
            and not order_id
        ):
            entities["courier_id"] = str(bound_courier)

    return True, None, entities, prefetched_order_route
