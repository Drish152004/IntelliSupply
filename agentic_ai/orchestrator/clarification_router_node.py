"""Single owner of HITL resume routing.

This node runs immediately after ``init_state`` and is the only place that
decides whether the current turn is a brand-new query or an answer to a prior
clarification. It owns the attempt cap and the merged-query construction
(``original_query`` + clarification answer) for intent/parameter resumes, and
routes each turn to the correct entry node.

Routing:
    new query        -> coarse_authorization
    domain answer     -> coarse_authorization
    intent answer     -> entity_extraction
    parameter answer  -> entity_extraction
    attempts exceeded -> response_formatter
"""

from __future__ import annotations

import json
import logging

from orchestrator.hitl_session import (
    STAGE_DOMAIN,
    STAGE_INTENT,
    STAGE_PARAMETER,
    apply_domain_session_to_state,
    attempts_exceeded,
    clarification_stage,
    get_active_hitl_session,
    merge_intent_query,
    parse_domain_answer,
)
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)


def _fail_attempts(state: AgentState) -> AgentState:
    return {
        **state,
        "clarification_failed": True,
        "agent_response": json.dumps(
            {
                "status": "clarification_failed",
                "message": "Clarification attempt limit reached.",
            },
            indent=2,
        ),
    }


def _resume_intent_or_parameter(
    state: AgentState,
    session: dict,
    *,
    stage: str,
    original: str,
) -> AgentState:
    """Hydrate task/domain/entities and build the merged query for the resume."""
    return {
        **state,
        "clarification_stage": stage,
        "original_query": original,
        "task": session.get("task") or state.get("task", ""),
        "domain": session.get("domain") or state.get("domain", ""),
        # Placed for entity_extraction to merge with freshly extracted entities.
        "entities": dict(session.get("entities") or {}),
        "user_query": merge_intent_query(original, state.get("user_query", "")),
    }


def _resume_domain(state: AgentState, *, original: str) -> AgentState:
    """Parse the domain answer and hand a resolved domain to coarse authorization.

    The raw answer is parsed here; the merged query is passed downstream so
    entity extraction / intent classification retain the original context.
    """
    answer = state.get("user_query", "")
    resolved = parse_domain_answer(answer)
    if not resolved:
        # Unresolved: let coarse authorization re-detect (and re-ask) normally.
        return {**state, "clarification_stage": None}

    routed = apply_domain_session_to_state(state, resolved)
    return {
        **routed,
        "clarification_stage": STAGE_DOMAIN,
        "original_query": original,
        "user_query": merge_intent_query(original, answer),
    }


def clarification_router(state: AgentState) -> AgentState:
    """Detect an active clarification session, enforce the attempt cap, and
    restore the context required to resume.

    This is the only resume owner. It hydrates ``task``/``domain``/``entities``
    from the session and builds the merged query (``original_query`` + answer)
    so downstream nodes can be phase-aware without inspecting sessions.
    """
    if state.get("clarification_failed"):
        return state

    session = get_active_hitl_session(state)
    if not session:
        # Brand-new query: nothing to resume.
        return state

    if attempts_exceeded(session):
        logger.info("Clarification attempt limit reached; failing turn.")
        return _fail_attempts(state)

    stage = clarification_stage(session)
    original = (
        session.get("original_query")
        or state.get("original_query")
        or state.get("user_query", "")
    )

    if stage in (STAGE_INTENT, STAGE_PARAMETER):
        updated = _resume_intent_or_parameter(state, session, stage=stage, original=original)
    elif stage == STAGE_DOMAIN:
        updated = _resume_domain(state, original=original)
    else:
        updated = {**state, "clarification_stage": stage}

    logger.info("clarification_router: stage=%s", stage)
    return updated


def route_after_clarification_router(state: AgentState) -> str:
    """Route to the correct entry node based on the resolved clarification stage.

    New / domain-answer turns go through the semantic cache lookup first; intent
    and parameter resumes (HITL) bypass the cache and resume at entity_extraction.
    """
    if state.get("clarification_failed"):
        return "response_formatter"
    if state.get("clarification_stage") in (STAGE_INTENT, STAGE_PARAMETER):
        return "entity_extraction"
    return "semantic_cache_lookup"
