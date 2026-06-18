"""Semantic cache lookup node.

Runs immediately after ``clarification_router`` for brand-new queries. On a hit it
short-circuits the pipeline straight to ``response_formatter``; on a miss it falls
through to ``coarse_authorization`` so the normal flow runs.

HITL turns never reach a productive lookup: resume turns are routed directly to
``entity_extraction`` by the clarification router, and this node additionally
self-guards on the clarification flags below (defense in depth). The cache itself
is fail-open -- any Redis error degrades to a miss.
"""

from __future__ import annotations

import logging

from cache.semantic_cache import semantic_lookup
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)


def _should_skip(state: AgentState) -> bool:
    """Skip the cache for any in-progress / failed clarification (HITL) turn."""
    return bool(
        state.get("clarification_needed")
        or state.get("clarification_failed")
        or state.get("clarification_stage") is not None
    )


def semantic_cache_lookup_node(state: AgentState) -> AgentState:
    """Look up the authenticated, role-scoped semantic cache for this query."""
    if _should_skip(state):
        return {**state, "cache_hit": False}

    user_id = state.get("authenticated_user_id")
    role = state.get("user_role")
    query = state.get("user_query", "")

    cached_response = semantic_lookup(query, user_id, role)
    if cached_response is not None:
        logger.info("semantic_cache_hit role=%s", role)
        return {**state, "cache_hit": True, "cache_response": cached_response}

    return {**state, "cache_hit": False}


def route_after_semantic_cache_lookup(state: AgentState) -> str:
    """Hit -> response_formatter (serve cached); miss -> coarse_authorization."""
    if state.get("cache_hit"):
        return "response_formatter"
    return "coarse_authorization"
