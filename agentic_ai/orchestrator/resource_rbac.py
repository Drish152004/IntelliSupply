"""Resource-level authorization: courier ownership and role boundaries."""

from __future__ import annotations

import re

from orchestrator.task_registry import (
    COURIER_RESOURCE_SCOPED_TASKS,
    INVENTORY_TASKS,
    LOGISTICS_RETRIEVAL_TASKS,
    SELF_SCOPED_PHRASES,
    is_task_allowed,
)
from context.entity_extractor import EntityExtractor
from orchestrator.state import AgentState


def detect_self_scoped_task(user_query: str) -> str | None:
    """Map first-person logistics phrases to a suggested task."""
    q = user_query.lower()
    for phrase, task in SELF_SCOPED_PHRASES:
        if phrase in q:
            return task
    if re.search(r"\b(?:my|mine)\b", q):
        return None
    return None


def apply_self_scoped_entities(
    *,
    entities: dict[str, str],
    user_query: str,
    user_role: str | None,
    session: dict | None,
) -> dict[str, str]:
    """Bind courier identity for 'my route' / 'my shipments' style queries."""
    resolved = dict(entities)
    q = user_query.lower()

    if any(phrase in q for phrase, _ in SELF_SCOPED_PHRASES) or re.search(r"\bmy\b", q):
        resolved["self_scoped"] = "true"

    bound = (session or {}).get("courier_id")
    if user_role == "COURIER" and bound:
        if resolved.get("self_scoped") == "true" or not resolved.get("courier_id"):
            resolved["courier_id"] = str(bound)

    if resolved.get("self_scoped") == "true" and bound and "courier_id" not in resolved:
        resolved["courier_id"] = str(bound)

    return resolved


def authorize_task_and_resources(state: AgentState) -> tuple[bool, str | None, dict[str, str]]:
    """
    Authorize after intent classification and entity extraction.

    Order: role present -> task allowed for role -> domain boundary -> courier resource scope.
    """
    role = state.get("user_role")
    task = state.get("task", "")
    domain = state.get("domain", "")

    entities = dict(state.get("entities") or {})
    if not entities and domain == "logistics":
        entities = EntityExtractor.extract(state["user_query"])

    entities = apply_self_scoped_entities(
        entities=entities,
        user_query=state["user_query"],
        user_role=role,
        session=state.get("logistics_session"),
    )

    if not role:
        return False, "User identity not provided", entities

    if role == "ADMIN":
        return True, None, entities

    if not is_task_allowed(role, task):
        return False, f"Role {role} is not allowed to execute {task}", entities

    if role == "INVENTORY" and (domain == "logistics" or task in LOGISTICS_RETRIEVAL_TASKS):
        return False, f"Role {role} cannot access logistics tasks", entities

    if role == "COURIER" and (domain == "inventory" or task in INVENTORY_TASKS):
        return False, "Couriers cannot access inventory queries", entities

    if role != "COURIER" or task not in COURIER_RESOURCE_SCOPED_TASKS:
        return True, None, entities

    session = state.get("logistics_session") or {}
    bound_courier = session.get("courier_id")
    if not bound_courier:
        return False, "Courier identity is not bound to this session", entities

    requested = entities.get("courier_id")
    if requested and str(requested) != str(bound_courier):
        return (
            False,
            f"You are not authorized to access courier {requested}'s data",
            entities,
        )

    if task in {"courier_lookup", "next_stop_lookup", "courier_route_lookup", "shipment_lookup"}:
        if not requested:
            entities["courier_id"] = str(bound_courier)

    return True, None, entities
