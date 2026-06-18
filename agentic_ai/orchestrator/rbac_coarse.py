"""Coarse authorization: domain detection, domain HITL, and domain-level RBAC."""

from __future__ import annotations

import json
import logging

from context.clarification_manager import ClarificationManager, ClarificationType
from orchestrator.hitl_session import (
    STAGE_DOMAIN,
    attach_clarification_session,
    build_clarification_session,
    clarification_type_for_stage,
)
from orchestrator.task_registry import (
    VALID_DOMAINS,
    coarse_domain_from_matches,
    match_coarse_domain_keywords,
)
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)

_ROLE_ALLOWED_DOMAINS: dict[str, frozenset[str]] = {
    "ADMIN": frozenset(VALID_DOMAINS),
    "INVENTORY": frozenset({"inventory"}),
    "COURIER": frozenset({"logistics"}),
    "LOGISTICS": frozenset({"logistics"}),
}


def is_domain_allowed_for_role(role: str | None, domain: str) -> bool:
    """Return whether a role may access the given domain at coarse authorization."""
    if not role:
        return False
    if role == "ADMIN":
        return True
    allowed = _ROLE_ALLOWED_DOMAINS.get(role, frozenset())
    return domain in allowed


def coarse_authorization(state: AgentState) -> AgentState:
    """
    Keyword-based domain detection, domain ambiguity HITL, and coarse RBAC.

    Domain-level permission only — no confidence scoring, task inference,
    resource ownership, or task authorization.

    Resume routing is owned entirely by clarification_router. A domain
    clarification answer arrives here with the domain already resolved on
    state; this node only validates role access for it.
    """
    if state.get("clarification_failed"):
        return state

    # Domain clarification answer: domain already resolved by clarification_router.
    if state.get("clarification_stage") == STAGE_DOMAIN and state.get("domain"):
        domain = state["domain"]
        role = state.get("user_role")
        base: AgentState = {
            **state,
            "coarse_domain": domain,
            "clarification_needed": False,
            "clarification_stage": None,
        }
        if not is_domain_allowed_for_role(role, domain):
            return _deny_domain_access(base, domain, role)
        logger.info("Domain clarification validated: domain=%s role=%s", domain, role)
        return _authorize_allowed(base, domain, classification_source="domain_resume")

    query = state["user_query"]
    role = state.get("user_role")

    # Domain detection is keyword-based only. Entity extraction is intentionally
    # not performed here; it runs later in the entity_extraction node.
    matched_inventory, matched_logistics = match_coarse_domain_keywords(query)
    domain = coarse_domain_from_matches(matched_inventory, matched_logistics)
    detection_source = "keyword"
    logger.info(
        "domain detection matched_inventory=%s matched_logistics=%s domain=%s source=%s",
        matched_inventory,
        matched_logistics,
        domain or "ambiguous",
        detection_source,
    )

    updated: AgentState = {
        **state,
        "coarse_domain": domain or "",
        "clarification_needed": False,
        "clarification_stage": None,
        "clarification_type": None,
        "clarification_question": None,
        "access_denied": False,
        "authorization_denied": False,
        "authorized": False,
        "authorized_domain": None,
    }

    if domain is None:
        logger.info(
            "domain=ambiguous source=keyword reason=no_unique_domain role=%s query=%r",
            role,
            query,
        )
        question = ClarificationManager.domain_question()
        return _request_domain_clarification(updated, question)

    logger.info("domain=%s source=%s role=%s", domain, detection_source, role)

    if not is_domain_allowed_for_role(role, domain):
        return _deny_domain_access(updated, domain, role)

    logger.info(
        "Coarse authorization allowed: domain=%s source=%s role=%s",
        domain,
        detection_source,
        role,
    )
    return _authorize_allowed(updated, domain, classification_source=detection_source)


def _authorize_allowed(
    state: AgentState,
    domain: str,
    *,
    classification_source: str,
) -> AgentState:
    return {
        **state,
        "coarse_domain": domain,
        "authorized": True,
        "authorized_domain": domain,
        "classification_source": classification_source,
        "clarification_needed": False,
        "clarification_stage": None,
        "access_denied": False,
        "authorization_denied": False,
    }


def _deny_domain_access(
    state: AgentState,
    domain: str,
    role: str | None,
) -> AgentState:
    role_label = role or "unknown"
    reason = f"Role {role_label} is not authorized to access {domain} domain"
    logger.info(
        "Coarse authorization denied: domain=%s source=keyword role=%s reason=%s",
        domain,
        role_label,
        reason,
    )
    return {
        **state,
        "coarse_domain": domain,
        "authorized": False,
        "authorized_domain": None,
        "classification_source": "keyword",
        "access_denied": True,
        "authorization_denied": False,
        "clarification_needed": False,
        "clarification_stage": None,
        "agent_response": json.dumps(
            {
                "status": "denied",
                "reason": reason,
                "domain": domain,
            },
            indent=2,
        ),
    }


def _request_domain_clarification(state: AgentState, question: str) -> AgentState:
    agent_response = json.dumps(
        {
            "status": "awaiting_input",
            "clarification_type": ClarificationType.DOMAIN.value,
            "question": question,
        },
        indent=2,
    )
    session = build_clarification_session(
        state,
        stage=STAGE_DOMAIN,
        clarification_type=clarification_type_for_stage(STAGE_DOMAIN),
    )
    updated: AgentState = {
        **state,
        "clarification_needed": True,
        "clarification_stage": STAGE_DOMAIN,
        "clarification_type": ClarificationType.DOMAIN.value,
        "clarification_question": question,
        "authorized": False,
        "authorized_domain": None,
        "classification_source": "keyword",
        "agent_response": agent_response,
    }
    return attach_clarification_session(updated, session, stage=STAGE_DOMAIN)
