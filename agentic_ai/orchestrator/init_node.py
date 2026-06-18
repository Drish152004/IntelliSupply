"""Initialize orchestrator state: identity, sessions, and multilingual normalization."""

from __future__ import annotations

import logging
from typing import Any

from integrations.language import normalize_query
from orchestrator.rbac.courier_identity import resolve_courier_identity
from orchestrator.rbac.session_context import merge_logistics_session, restore_user_role
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)


def _bootstrap_identity(
    *,
    user_role: str | None,
    authenticated_user: dict | None,
    logistics_session: dict | None,
    inventory_session: dict | None,
    pending_clarification_session: dict | None,
) -> tuple[str | None, dict | None, dict[str, Any]]:
    identity_fields: dict[str, Any] = {}
    if authenticated_user:
        identity = resolve_courier_identity(authenticated_user)
        resolved_role = identity["user_role"]
        resolved_logistics = merge_logistics_session(
            logistics_session,
            identity.get("logistics_session"),
        )
        courier_id = authenticated_user.get("courier_id")
        if courier_id is None and resolved_logistics:
            courier_id = resolved_logistics.get("courier_id")
        identity_fields = {
            "authenticated_user_id": identity.get("user_id"),
            "authenticated_email": identity.get("email"),
            "authenticated_name": identity.get("name"),
            "authenticated_role_id": identity.get("role_id"),
            "authenticated_courier_id": str(courier_id).strip() if courier_id else None,
        }
        # Courier identity binding (new model): bind the JWT courier name only for
        # COURIER users. ADMIN/LOGISTICS/INVENTORY identities are never auto-bound;
        # they continue to provide the courier explicitly via clarification.
        if resolved_role == "COURIER":
            name = identity.get("name")
            identity_fields["bound_courier_name"] = (
                str(name).strip() if name and str(name).strip() else None
            )
        return resolved_role, resolved_logistics, identity_fields

    resolved_role = restore_user_role(
        user_role=user_role,
        logistics_session=logistics_session,
        inventory_session=inventory_session,
        pending_clarification_session=pending_clarification_session,
    )
    return resolved_role, logistics_session, identity_fields


def init_state(state: AgentState) -> AgentState:
    """Bootstrap identity, sessions, and English-normalized query."""
    user_query = state.get("user_query", "")
    language_hint = state.get("language_hint")

    normalized = normalize_query(user_query, language_hint=language_hint)

    resolved_role, resolved_logistics, identity_fields = _bootstrap_identity(
        user_role=state.get("user_role"),
        authenticated_user=state.get("authenticated_user"),
        logistics_session=state.get("logistics_session"),
        inventory_session=state.get("inventory_session"),
        pending_clarification_session=state.get("pending_clarification_session"),
    )

    updated: AgentState = {
        **state,
        **identity_fields,
        "original_query": normalized["original_query"],
        "user_query": normalized["user_query"],
        "detected_language": normalized["detected_language"],
        "user_role": resolved_role,
        "access_denied": False,
        "authorization_denied": False,
        "clarification_needed": False,
        "clarification_failed": False,
    }

    if resolved_logistics:
        updated["logistics_session"] = resolved_logistics
    if state.get("inventory_session"):
        updated["inventory_session"] = state["inventory_session"]
    if state.get("pending_clarification_session"):
        updated["pending_clarification_session"] = state["pending_clarification_session"]

    logger.info(
        "init_state: user_id=%s role=%s courier_id=%s bound_courier_name=%s",
        updated.get("authenticated_user_id", ""),
        updated.get("user_role", ""),
        updated.get("authenticated_courier_id", ""),
        updated.get("bound_courier_name", ""),
    )
    return updated


def build_initial_state(
    user_query: str,
    *,
    ml_payload_partial: dict | None = None,
    logistics_session: dict | None = None,
    inventory_session: dict | None = None,
    pending_clarification_session: dict | None = None,
    user_role: str | None = None,
    authenticated_user: dict | None = None,
    language_hint: str | None = None,
) -> AgentState:
    """Build minimal state passed to the graph entrypoint."""
    initial: AgentState = {
        "user_query": user_query,
        "original_query": user_query,
        "detected_language": "en",
        "domain": "",
        "coarse_domain": "",
        "task": "",
        "confidence": 0.0,
        "agent_response": "",
        "final_response": "",
        "access_denied": False,
        "authorization_denied": False,
        "entities": {},
        "missing_fields": [],
        "clarification_needed": False,
        "clarification_failed": False,
        "clarification_type": None,
        "clarification_question": None,
        "function_name": None,
        "payload": {},
        "execution_status": None,
        "execution_error": None,
    }
    if ml_payload_partial:
        initial["ml_payload_partial"] = ml_payload_partial
    if logistics_session:
        initial["logistics_session"] = logistics_session
    if inventory_session:
        initial["inventory_session"] = inventory_session
    if pending_clarification_session:
        initial["pending_clarification_session"] = pending_clarification_session
    if user_role:
        initial["user_role"] = user_role
    if authenticated_user:
        initial["authenticated_user"] = authenticated_user
    if language_hint:
        initial["language_hint"] = language_hint
    return initial
