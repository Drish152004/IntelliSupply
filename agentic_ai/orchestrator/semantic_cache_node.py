"""LangGraph nodes for semantic cache lookup and store."""

from __future__ import annotations

import json
import logging

from cache.cache_scope import build_entity_signature, build_identity_scope
from cache.semantic_cache import get_semantic_cache
from observability.trace_events import trace_cache_lookup, trace_cache_store
from orchestrator.intent_task_classifier import needs_intent_clarification
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)


def should_persist_to_cache(state: AgentState) -> bool:
    """Return True only for successful RAG executions that should be cached."""
    if state.get("cache_hit"):
        return False
    if state.get("clarification_needed"):
        return False
    if state.get("access_denied") or state.get("authorization_denied"):
        return False
    if state.get("execution_status") != "success":
        return False
    if state.get("execution_error"):
        return False
    if needs_intent_clarification(state.get("task", ""), state.get("confidence", 1.0)):
        return False
    return True


def lookup_semantic_cache(state: AgentState) -> AgentState:
    """Look up a semantically similar cached response after intent classification."""
    query = state["user_query"]
    role = state.get("user_role") or ""
    domain = state.get("domain") or state.get("authorized_domain") or state.get("coarse_domain") or ""
    task = state.get("task", "")
    entity_signature = build_entity_signature(state)
    identity_scope = build_identity_scope(state)
    trace_id = state.get("trace_id")

    logger.info(
        "semantic_cache_lookup: domain=%s task=%s entity=%s identity=%s confidence=%s",
        domain,
        task,
        entity_signature,
        identity_scope,
        state.get("confidence"),
    )

    if identity_scope.startswith("unauthenticated:"):
        logger.info(
            "cache lookup skipped for unauthenticated identity=%s",
            identity_scope,
        )
        trace_cache_lookup(
            {
                "query": query,
                "cache_key": None,
                "hit": False,
                "skipped": True,
                "reason": "unauthenticated",
            },
            trace_id=trace_id,
        )
        return {**state, "cache_hit": False, "cache_key": None, "cached_result": None}

    hit, key, cached, score = get_semantic_cache().lookup(
        query,
        role=role,
        domain=domain,
        task=task,
        entity_signature=entity_signature,
        identity_scope=identity_scope,
    )

    trace_cache_lookup(
        {
            "query": query,
            "cache_key": key,
            "hit": hit,
            "score": score,
            "task": task,
            "domain": domain,
        },
        trace_id=trace_id,
    )

    if not hit:
        logger.info(
            "cache miss task=%s entity=%s identity=%s",
            task,
            entity_signature,
            identity_scope,
        )
        return {**state, "cache_hit": False, "cache_key": None, "cached_result": None}

    logger.info(
        "cache hit task=%s entity=%s identity=%s score=%.3f key=%s",
        task,
        entity_signature,
        identity_scope,
        score,
        key,
    )
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
    """Store finalized successful RAG results in the semantic cache."""
    if not should_persist_to_cache(state):
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
    domain = state.get("domain") or state.get("authorized_domain") or ""
    entity_signature = build_entity_signature(state)
    identity_scope = build_identity_scope(state)
    trace_id = state.get("trace_id")

    if identity_scope.startswith("unauthenticated:"):
        logger.info(
            "cache store skipped for unauthenticated identity=%s",
            identity_scope,
        )
        return state

    key = get_semantic_cache().store(
        state["user_query"],
        result,
        role=role,
        domain=domain,
        task=task,
        entity_signature=entity_signature,
        identity_scope=identity_scope,
    )

    payload_size = len(json.dumps(result, default=str).encode("utf-8"))
    trace_cache_store(
        {
            "cache_key": key,
            "payload_size": payload_size,
            "task": task,
            "domain": domain,
        },
        trace_id=trace_id,
    )

    logger.info(
        "cache store complete task=%s domain=%s entity=%s identity=%s key=%s",
        task,
        domain,
        entity_signature,
        identity_scope,
        key,
    )

    return {**state, "cache_key": key}
