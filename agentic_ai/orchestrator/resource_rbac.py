"""Resource-level authorization: courier ownership and role boundaries."""

from __future__ import annotations

from typing import Any

from integrations.aura_bridge import fetch_order_route
from orchestrator.task_registry import COURIER_RESOURCE_SCOPED_TASKS, is_task_allowed
from orchestrator.state import AgentState


def authorize_task_and_resources(
    state: AgentState,
) -> tuple[bool, str | None, dict[str, str], dict[str, Any] | None]:
    """
    Authorize after intent classification and entity extraction.

    Order: role present -> task allowed for role -> courier resource ownership.

    Courier ownership is resource-based, not task-based:
      * any ``order_id`` present is verified against the JWT/session courier,
        regardless of which task is executing;
      * any requested ``courier_id`` must equal the JWT/session courier;
      * when no specific resource is requested, the courier is confined to their
        own data by binding the JWT/session courier_id.

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

    if role != "COURIER":
        return True, None, entities, None

    session = state.get("logistics_session") or {}
    bound_courier = session.get("courier_id")
    if not bound_courier:
        return False, "Courier identity is not bound to this session", entities, None

    # Resource ownership (courier_id): a courier may only target their own id.
    requested = entities.get("courier_id")
    if requested and str(requested) != str(bound_courier):
        return (
            False,
            f"You are not authorized to access courier {requested}'s data",
            entities,
            None,
        )

    # Resource ownership (order_id): verify the order belongs to this courier,
    # independent of the task name. Any task carrying an order_id is checked.
    order_id = entities.get("order_id")
    if order_id:
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

    # Confine the courier to their own data: when no specific resource was
    # requested, force the bound courier_id so scoped tasks (recent_routes,
    # courier_orders, courier_route) never execute unscoped.
    if not requested and not order_id and task in COURIER_RESOURCE_SCOPED_TASKS:
        entities["courier_id"] = str(bound_courier)

    return True, None, entities, prefetched_order_route
