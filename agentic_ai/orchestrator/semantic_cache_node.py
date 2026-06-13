"""LangGraph nodes for semantic cache lookup and store."""

from __future__ import annotations

import json
import logging

from cache.semantic_cache import get_semantic_cache
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)


def lookup_semantic_cache(state: AgentState) -> AgentState:
    """Look up a semantically similar cached response."""
    query = state["user_query"]
    role = state.get("user_role") or ""
    domain = state.get("coarse_domain") or state.get("domain") or ""

    hit, key, cached = get_semantic_cache().lookup(
        query,
        role=role,
        domain=domain,
    )

    if not hit:
        return {**state, "cache_hit": False, "cache_key": None, "cached_result": None}

    return {
        **state,
        "cache_hit": True,
        "cache_key": key,
        "cached_result": cached,
        "agent_response": json.dumps(
            {"status": "complete", "result": cached, "source": "cache"},
            indent=2,
            default=str,
        ),
    }


def store_semantic_cache(state: AgentState) -> AgentState:
    """Store successful RAG results in the semantic cache."""
    if state.get("cache_hit"):
        return state

    raw = state.get("agent_response", "")
    if not raw:
        return state

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return state

    if payload.get("status") not in {"complete", "success"}:
        return state

    result = payload.get("result") or payload.get("data") or payload
    task = state.get("task", "")
    role = state.get("user_role") or ""
    domain = state.get("domain") or ""

    key = get_semantic_cache().store(
        state["user_query"],
        result,
        role=role,
        domain=domain,
        task=task,
    )

    return {**state, "cache_key": key}
