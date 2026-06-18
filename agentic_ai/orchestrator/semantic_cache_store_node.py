"""Semantic cache store node.

Runs after ``response_formatter`` as the final hop before END. It persists only
clean, successful, fully-authorized responses. Clarification questions, HITL
turns, authorization/access failures, execution errors, empty responses, and
responses that were themselves served from cache are never written.

Storing is fail-open: a Redis error is swallowed inside the cache layer and the
node returns state unchanged either way.
"""

from __future__ import annotations

import logging

from cache.semantic_cache import semantic_store
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)

_CACHEABLE_STATUSES = {"success", "complete"}


def _should_store(state: AgentState) -> bool:
    if state.get("cache_hit"):
        # Already served from cache; nothing new to persist.
        return False
    if state.get("execution_status") not in _CACHEABLE_STATUSES:
        return False
    if state.get("clarification_needed"):
        return False
    if state.get("clarification_failed"):
        return False
    if state.get("authorization_denied"):
        return False
    if state.get("access_denied"):
        return False
    if not (state.get("final_response") or "").strip():
        return False
    return True


def semantic_cache_store_node(state: AgentState) -> AgentState:
    """Persist a successful, authorized final_response into the semantic cache."""
    if not _should_store(state):
        return state

    user_id = state.get("authenticated_user_id")
    role = state.get("user_role")
    query = state.get("user_query", "")

    semantic_store(query, state.get("final_response"), user_id, role)
    return state
