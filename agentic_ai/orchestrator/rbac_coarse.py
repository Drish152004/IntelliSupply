"""Coarse authorization: domain detection, domain HITL, and domain-level RBAC."""

from __future__ import annotations

import json
import logging

from context.clarification_manager import ClarificationManager, ClarificationType
from context.entity_extractor import EntityExtractor
from context.self_scoped import is_self_scoped_query
from orchestrator.hitl_session import (
    STAGE_DOMAIN,
    STAGE_PARAMETER,
    apply_domain_session_to_state,
    attach_clarification_session,
    build_clarification_session,
    clarification_type_for_stage,
    get_active_hitl_session,
    is_domain_resume,
    is_parameter_resume,
    parse_domain_answer,
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

# Presence of any of these extracted entities uniquely implies the logistics domain.
# Includes both spec field names and the variant keys the extractor actually emits
# (e.g. from_hub/to_hub, courier_reference, city).
_LOGISTICS_ENTITY_KEYS: frozenset[str] = frozenset({
    "order_id",
    "shipment_id",
    "courier_id",
    "courier_name",
    "courier_reference",
    "hub_id",
    "from_hub_id",
    "to_hub_id",
    "from_hub",
    "to_hub",
    "city_name",
    "city",
    "route_prediction_id",
    "self_scoped",
})

# Presence of any of these extracted entities uniquely implies the inventory domain.
_INVENTORY_ENTITY_KEYS: frozenset[str] = frozenset({
    "sku_id",
    "warehouse_id",
    "product_name",
})


def domain_from_entities(entities: dict[str, str] | None) -> str | None:
    """
    Resolve a domain from extracted entities, or None when undetermined.

    Entity-based routing takes precedence over keyword matching. When entities
    from both domains are present, the result is ambiguous (None) so keyword
    detection can arbitrate.
    """
    if not entities:
        return None
    has_logistics = any(entities.get(key) for key in _LOGISTICS_ENTITY_KEYS)
    has_inventory = any(entities.get(key) for key in _INVENTORY_ENTITY_KEYS)
    if has_logistics and not has_inventory:
        return "logistics"
    if has_inventory and not has_logistics:
        return "inventory"
    return None


def _entities_for_domain_detection(state: AgentState, query: str) -> dict[str, str]:
    """
    Return entities to drive domain detection.

    Prefers entities already on state; falls back to a deterministic extraction
    because coarse authorization runs before the entity_extraction node. This is
    side-effect free and does not alter the entities the pipeline later produces.
    """
    existing = state.get("entities") or {}
    if existing:
        return existing
    extracted = dict(EntityExtractor.extract(query))
    if "self_scoped" not in extracted and is_self_scoped_query(query):
        extracted["self_scoped"] = "true"
    return extracted


def is_domain_allowed_for_role(role: str | None, domain: str) -> bool:
    """Return whether a role may access the given domain at coarse authorization."""
    if not role:
        return False
    if role == "ADMIN":
        return True
    allowed = _ROLE_ALLOWED_DOMAINS.get(role, frozenset())
    return domain in allowed


def _resume_parameter_domain(state: AgentState) -> AgentState:
    """Skip domain detection when resuming parameter clarification."""
    session = get_active_hitl_session(state) or {}
    domain = session.get("domain") or state.get("domain", "")
    logger.info(
        "Coarse authorization allowed: domain=%s source=parameter_resume role=%s",
        domain,
        state.get("user_role"),
    )
    return _authorize_allowed(state, domain, classification_source="parameter_resume")


def _resume_domain_clarification(state: AgentState) -> AgentState:
    """Interpret the user's domain answer and route into the correct session bucket."""
    query = state["user_query"]
    role = state.get("user_role")
    resolved = parse_domain_answer(query)

    if resolved is None:
        question = ClarificationManager.domain_question()
        return _request_domain_clarification(state, question)

    if not is_domain_allowed_for_role(role, resolved):
        return _deny_domain_access(state, resolved, role)

    logger.info(
        "Domain clarification resolved: domain=%s source=user_answer role=%s query=%r",
        resolved,
        role,
        query,
    )
    routed = apply_domain_session_to_state(state, resolved)
    return _authorize_allowed(routed, resolved, classification_source="domain_resume")


def coarse_authorization(state: AgentState) -> AgentState:
    """
    Keyword-based domain detection, domain ambiguity HITL, and coarse RBAC.

    Domain-level permission only — no confidence scoring, task inference,
    resource ownership, or task authorization.
    """
    if state.get("clarification_failed"):
        return state

    if is_domain_resume(state):
        return _resume_domain_clarification(state)

    if is_parameter_resume(state):
        return _resume_parameter_domain(state)

    query = state["user_query"]
    role = state.get("user_role")

    # Entity-based routing takes precedence over keyword matching: a present
    # logistics/inventory entity is sufficient to determine the domain.
    entities = _entities_for_domain_detection(state, query)
    entity_domain = domain_from_entities(entities)

    matched_inventory, matched_logistics = match_coarse_domain_keywords(query)
    logger.info(
        "keyword matches inventory=%s logistics=%s query=%r",
        matched_inventory,
        matched_logistics,
        query,
    )
    keyword_domain = coarse_domain_from_matches(matched_inventory, matched_logistics)

    domain = entity_domain or keyword_domain
    detection_source = "entity" if entity_domain else "keyword"
    logger.info(
        "domain detection entity_domain=%s matched_inventory=%s matched_logistics=%s "
        "domain=%s source=%s",
        entity_domain or "none",
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
