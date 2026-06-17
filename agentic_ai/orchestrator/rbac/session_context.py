"""Persist and restore RBAC context across multi-turn orchestrator sessions."""

from __future__ import annotations

from typing import Any

from orchestrator.hitl_session import build_session_for_response as hitl_build_session_for_response
from orchestrator.rbac.role_mapper import map_to_orchestrator_role
from orchestrator.state import AgentState


def restore_user_role(
    *,
    user_role: str | None,
    logistics_session: dict[str, Any] | None,
    inventory_session: dict[str, Any] | None,
    pending_clarification_session: dict[str, Any] | None = None,
) -> str | None:
    """Restore mapped role from explicit argument or persisted session."""
    if user_role is not None and str(user_role).strip():
        return map_to_orchestrator_role(user_role)

    for session in (pending_clarification_session, logistics_session, inventory_session):
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


def build_session_for_response(state: AgentState) -> dict[str, Any] | None:
    """Build session payload embedded in clarification responses."""
    return hitl_build_session_for_response(state)
