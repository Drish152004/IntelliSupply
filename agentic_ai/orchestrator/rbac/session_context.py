"""Persist and restore RBAC context across multi-turn orchestrator sessions."""

from __future__ import annotations

from typing import Any

from orchestrator.rbac.role_mapper import map_to_orchestrator_role
from orchestrator.state import AgentState


def restore_user_role(
    *,
    user_role: str | None,
    logistics_session: dict[str, Any] | None,
    inventory_session: dict[str, Any] | None,
) -> str | None:
    """Restore mapped role from explicit argument or persisted session."""
    if user_role is not None and str(user_role).strip():
        return map_to_orchestrator_role(user_role)

    for session in (logistics_session, inventory_session):
        if session and session.get("user_role"):
            return map_to_orchestrator_role(session["user_role"])

    return None


def merge_logistics_session(
    base: dict[str, Any] | None,
    overrides: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Merge courier identity and RBAC fields into a logistics session."""
    if not base and not overrides:
        return None
    merged = dict(base or {})
    if overrides:
        merged.update(overrides)
    return merged


def persist_rbac_context(
    session: dict[str, Any] | None,
    *,
    user_role: str | None,
    task: str,
    courier_id: str | None = None,
) -> dict[str, Any]:
    """Persist role, task, and courier_id for continuation turns."""
    persisted = dict(session or {})
    if user_role:
        persisted["user_role"] = user_role
    if task:
        persisted["task"] = task
    if courier_id:
        persisted["courier_id"] = courier_id
    elif persisted.get("courier_id"):
        pass
    return persisted


def build_session_for_response(state: AgentState) -> dict[str, Any] | None:
    """Build session payload embedded in clarification responses."""
    domain = state.get("domain", "")
    logistics = state.get("logistics_session")
    inventory = state.get("inventory_session")

    if domain == "inventory":
        base = dict(inventory or {})
    else:
        base = dict(logistics or {})

    courier_id = None
    if logistics and logistics.get("courier_id"):
        courier_id = logistics["courier_id"]

    persisted = persist_rbac_context(
        base,
        user_role=state.get("user_role"),
        task=state.get("task", ""),
        courier_id=courier_id,
    )

    if domain == "inventory" and state.get("inventory_session"):
        collecting = state["inventory_session"].get("collecting")
        if collecting:
            persisted["collecting"] = collecting
        messages = state["inventory_session"].get("messages")
        if messages:
            persisted["messages"] = messages

    if domain != "inventory" and logistics:
        collecting = logistics.get("collecting")
        if collecting:
            persisted["collecting"] = collecting
        messages = logistics.get("messages")
        if messages:
            persisted["messages"] = messages

    if state.get("clarification_needed"):
        persisted["collecting"] = True

    return persisted or None
