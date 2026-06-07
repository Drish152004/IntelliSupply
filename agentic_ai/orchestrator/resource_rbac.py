"""Shared resource-level RBAC checks for graph and ML paths."""

from __future__ import annotations

from context.entity_extractor import EntityExtractor
from graph_retrieval.graph_authorizer import COURIER_SCOPED_TASKS, GraphAuthorizer
from orchestrator.state import AgentState


def _entities_for_resource_check(state: AgentState) -> dict[str, str]:
    entities = dict(state.get("entities") or {})
    if not entities:
        entities = EntityExtractor.extract(state["user_query"])

    entities = GraphAuthorizer.resolve_courier_id(
        entities=entities,
        user_query=state["user_query"],
        session=state.get("logistics_session"),
    )

    for payload_key in ("payload", "ml_payload_partial"):
        payload = state.get(payload_key)
        if not isinstance(payload, dict):
            continue
        if payload.get("courier_id") and "courier_id" not in entities:
            entities["courier_id"] = str(payload["courier_id"])
        if payload.get("delivery_user_id") and "courier_id" not in entities:
            entities["courier_id"] = str(payload["delivery_user_id"])

    return entities


def authorize_courier_resource(state: AgentState) -> tuple[bool, str | None, dict[str, str]]:
    """
    Return (allowed, denial_reason, resolved_entities).

    Applies GraphAuthorizer rules consistently for graph and ML execution paths.
    """
    task = state.get("task", "")
    if task not in COURIER_SCOPED_TASKS:
        return True, None, dict(state.get("entities") or {})

    role = state.get("user_role")
    if not role:
        return False, "User identity not provided", dict(state.get("entities") or {})

    entities = _entities_for_resource_check(state)
    allowed, reason = GraphAuthorizer.check(
        role=role,
        task=task,
        entities=entities,
        user_query=state["user_query"],
        session=state.get("logistics_session"),
    )
    return allowed, reason, entities
