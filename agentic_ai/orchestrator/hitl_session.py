"""Stage-aware HITL session persistence, resume, and entity merge."""

from __future__ import annotations

import re
from typing import Any

from context.clarification_manager import ClarificationType
from orchestrator.state import AgentState

MAX_HITL_ATTEMPTS = 3

STAGE_DOMAIN = "domain"
STAGE_INTENT = "intent"
STAGE_PARAMETER = "parameter"

_INVENTORY_DOMAIN_ALIASES = frozenset({
    "inventory",
    "stock",
    "stocks",
    "product",
    "products",
    "warehouse",
})

_LOGISTICS_DOMAIN_ALIASES = frozenset({
    "logistics",
    "shipment",
    "shipments",
    "order",
    "orders",
    "route",
    "routes",
    "eta",
    "courier",
    "couriers",
    "hub",
    "hubs",
    "delivery",
    "tracking",
})


def get_active_hitl_session(state: AgentState) -> dict[str, Any] | None:
    """Return the session driving an in-progress clarification workflow."""
    pending = state.get("pending_clarification_session")
    if pending and pending.get("collecting"):
        return pending

    for session in (state.get("inventory_session"), state.get("logistics_session")):
        if session and session.get("collecting"):
            return session
    return None


def clarification_stage(session: dict[str, Any] | None) -> str | None:
    if not session:
        return None
    stage = session.get("clarification_stage")
    return str(stage) if stage else None


def parse_domain_answer(user_query: str) -> str | None:
    """Interpret a user's domain clarification reply."""
    normalized = user_query.strip().lower()
    tokens = set(re.findall(r"\b\w+\b", normalized))

    inventory_hits = tokens & _INVENTORY_DOMAIN_ALIASES
    logistics_hits = tokens & _LOGISTICS_DOMAIN_ALIASES

    if inventory_hits and not logistics_hits:
        return "inventory"
    if logistics_hits and not inventory_hits:
        return "logistics"

    if "inventory" in normalized or "stock" in normalized:
        if "logistics" not in normalized and "shipment" not in normalized:
            return "inventory"
    if any(word in normalized for word in ("logistics", "shipment", "courier", "route", "eta")):
        if "inventory" not in normalized and "stock" not in normalized:
            return "logistics"
    return None


def merge_intent_query(original_query: str, clarification_answer: str) -> str:
    """Combine the original vague query with the user's intent clarification."""
    original = original_query.strip()
    answer = clarification_answer.strip()
    if not original:
        return answer
    if not answer:
        return original
    return f"{original} {answer}"


def merge_entities(
    persisted: dict[str, str] | None,
    extracted: dict[str, str],
) -> dict[str, str]:
    """Merge persisted clarification entities with newly extracted ones."""
    merged = dict(persisted or {})
    merged.update(extracted)
    return merged


def current_clarification_attempts(session: dict[str, Any] | None) -> int:
    if not session:
        return 0
    try:
        return int(session.get("clarification_attempts", 0))
    except (TypeError, ValueError):
        return 0


def next_clarification_attempts(session: dict[str, Any] | None) -> int:
    return current_clarification_attempts(session) + 1


def attempts_exceeded(session: dict[str, Any] | None) -> bool:
    return current_clarification_attempts(session) >= MAX_HITL_ATTEMPTS


def build_clarification_session(
    state: AgentState,
    *,
    stage: str,
    clarification_type: str,
    base_session: dict[str, Any] | None = None,
    candidate_tasks: list[str] | None = None,
) -> dict[str, Any]:
    """Persist clarification metadata for the next client turn."""
    session = dict(base_session or {})
    original = state.get("original_query") or state.get("user_query", "")

    session["collecting"] = True
    session["clarification_stage"] = stage
    session["clarification_type"] = clarification_type
    session["original_query"] = original
    session["task"] = state.get("task", "") or session.get("task", "")
    session["domain"] = state.get("domain", "") or session.get("domain", "")

    if state.get("user_role"):
        session["user_role"] = state["user_role"]

    logistics = state.get("logistics_session") or {}
    if logistics.get("courier_id"):
        session["courier_id"] = logistics["courier_id"]
    elif state.get("authenticated_courier_id"):
        session["courier_id"] = state["authenticated_courier_id"]

    entities = state.get("entities") or {}
    if entities:
        session["entities"] = dict(entities)

    if candidate_tasks:
        session["candidate_tasks"] = list(candidate_tasks)

    session["clarification_attempts"] = next_clarification_attempts(session)
    return session


def route_resolved_domain_session(
    state: AgentState,
    domain: str,
    *,
    base_session: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a domain-specific session after domain clarification resolves."""
    session = dict(base_session or {})
    session["domain"] = domain
    session.pop("clarification_stage", None)
    session.pop("clarification_type", None)
    session.pop("original_query", None)
    session.pop("clarification_attempts", None)
    session["collecting"] = False

    if state.get("user_role"):
        session["user_role"] = state["user_role"]
    if state.get("authenticated_courier_id"):
        session["courier_id"] = state["authenticated_courier_id"]
    return session


def apply_domain_session_to_state(state: AgentState, domain: str) -> AgentState:
    """Route a resolved domain into the correct domain session bucket."""
    pending = dict(state.get("pending_clarification_session") or {})
    routed = route_resolved_domain_session(state, domain, base_session=pending)

    updated: AgentState = {
        **state,
        "domain": domain,
        "coarse_domain": domain,
        "pending_clarification_session": None,
    }

    # The opposite bucket is already preserved by the ``**state`` spread above;
    # only the resolved domain's bucket needs to be replaced with the routed one.
    if domain == "inventory":
        updated["inventory_session"] = routed
    else:
        updated["logistics_session"] = routed

    return updated


def attach_clarification_session(
    state: AgentState,
    session: dict[str, Any],
    *,
    stage: str,
) -> AgentState:
    """Attach a clarification session to the correct state bucket."""
    if stage == STAGE_DOMAIN:
        return {**state, "pending_clarification_session": session}

    domain = session.get("domain") or state.get("domain", "")
    if domain == "inventory":
        return {**state, "inventory_session": session}
    return {**state, "logistics_session": session}


HITL_ACTIVE_RESPONSE_STATUS = "clarification_required"


def should_clear_hitl_sessions(response_status: str | None) -> bool:
    """Return True when a terminal response should not retain HITL session state."""
    return response_status != HITL_ACTIVE_RESPONSE_STATUS


def _strip_session_hitl(session: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return a copy of a session bucket with HITL collection fields removed."""
    if not session:
        return session
    cleaned = dict(session)
    cleaned["collecting"] = False
    for field in (
        "clarification_stage",
        "clarification_type",
        "original_query",
        "clarification_attempts",
        "entities",
        "candidate_tasks",
    ):
        cleaned.pop(field, None)
    return cleaned


def clear_all_hitl_sessions(state: AgentState) -> AgentState:
    """Clear HITL state from all session buckets after a terminal response."""
    updated: AgentState = {**state, "pending_clarification_session": None}

    logistics = _strip_session_hitl(state.get("logistics_session"))
    if logistics is not None:
        updated["logistics_session"] = logistics

    inventory = _strip_session_hitl(state.get("inventory_session"))
    if inventory is not None:
        updated["inventory_session"] = inventory

    return updated


def build_session_for_response(state: AgentState) -> dict[str, Any] | None:
    """Build the session payload returned to clients during clarification."""
    if state.get("clarification_needed"):
        pending = state.get("pending_clarification_session")
        if pending and pending.get("collecting"):
            return dict(pending)

        active = get_active_hitl_session(state)
        if active:
            return dict(active)

    if state.get("execution_status") in {"success", "complete"}:
        return None

    return None


def clarification_type_for_stage(stage: str) -> str:
    mapping = {
        STAGE_DOMAIN: ClarificationType.DOMAIN.value,
        STAGE_INTENT: ClarificationType.INTENT.value,
        STAGE_PARAMETER: ClarificationType.ENTITY.value,
    }
    return mapping.get(stage, ClarificationType.INTENT.value)
