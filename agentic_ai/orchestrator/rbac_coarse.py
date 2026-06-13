"""Domain routing hints — not a final authorization layer."""

from __future__ import annotations

import json
import logging

from context.clarification_manager import ClarificationManager, ClarificationType
from orchestrator.task_registry import detect_coarse_domain
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)

_ROLE_DEFAULT_DOMAIN: dict[str, str] = {
    "INVENTORY": "inventory",
    "COURIER": "logistics",
    "LOGISTICS": "logistics",
}


def _session_collecting(state: AgentState) -> bool:
    for key in ("logistics_session", "inventory_session"):
        session = state.get(key)
        if session and session.get("collecting"):
            return True
    return False


def apply_domain_routing_hint(state: AgentState) -> AgentState:
    """
    Infer likely domain for cache partitioning and intent bias.

    Never denies access. ADMIN always passes. Ambiguous queries trigger DOMAIN HITL.
    """
    if _session_collecting(state):
        session = state.get("logistics_session") or state.get("inventory_session") or {}
        domain = session.get("domain") or ("logistics" if state.get("logistics_session") else "inventory")
        return {**state, "coarse_domain": domain, "clarification_needed": False}

    query = state["user_query"]
    role = state.get("user_role")

    domain, confidence, ambiguous = detect_coarse_domain(query)

    updated: AgentState = {
        **state,
        "coarse_domain": domain or "",
        "clarification_needed": False,
        "clarification_type": None,
        "clarification_question": None,
        "access_denied": False,
    }

    if role == "ADMIN":
        if domain:
            updated["coarse_domain"] = domain
        return updated

    if role in _ROLE_DEFAULT_DOMAIN and (ambiguous or not domain):
        return {**updated, "coarse_domain": _ROLE_DEFAULT_DOMAIN[role]}

    if ambiguous or not domain:
        question = ClarificationManager.domain_question()
        return _request_domain_clarification(updated, question)

    logger.debug(
        "Domain routing hint: domain=%s confidence=%s role=%s",
        domain,
        confidence,
        role,
    )
    return {**updated, "coarse_domain": domain}


def _request_domain_clarification(state: AgentState, question: str) -> AgentState:
    agent_response = json.dumps(
        {
            "status": "awaiting_input",
            "clarification_type": ClarificationType.DOMAIN.value,
            "question": question,
        },
        indent=2,
    )
    return {
        **state,
        "clarification_needed": True,
        "clarification_type": ClarificationType.DOMAIN.value,
        "clarification_question": question,
        "agent_response": agent_response,
    }


# Backward-compatible alias for graph node registration.
enforce_rbac_coarse = apply_domain_routing_hint
