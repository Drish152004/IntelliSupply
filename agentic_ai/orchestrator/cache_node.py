"""
Cache lookup and store nodes for the orchestration graph.

Runs after RBAC and before agent routing. Stores business results after
successful agent execution for cacheable tasks.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from cache.cache_key_builder import CacheKeyBuilder
from cache.cache_service import CacheService
from cache.ttl_config import is_cacheable, ttl_for_task
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)

_cache_service = CacheService()


def get_cache_service() -> CacheService:
    """Return the shared cache service instance (for tests)."""
    return _cache_service


def reset_cache_service(service: CacheService | None = None) -> None:
    """Replace or reset the shared cache service (for tests)."""
    global _cache_service
    _cache_service = service if service is not None else CacheService()
    if service is None:
        _cache_service.clear()


def extract_business_result(response_payload: dict[str, Any]) -> dict[str, Any] | None:
    """Extract structured business data from an agent response payload."""
    business_result = response_payload.get("business_result")
    if isinstance(business_result, dict):
        return business_result

    result = response_payload.get("result")
    if isinstance(result, dict):
        return result

    return None


def _agent_name_for_domain(domain: str) -> str:
    return domain if domain in {"inventory", "logistics"} else "logistics"


def lookup_cache(state: AgentState) -> AgentState:
    """Attempt a cache lookup for cacheable tasks."""
    task = state.get("task", "")
    updated: AgentState = {
        **state,
        "cache_hit": False,
        "cache_key": None,
        "cached_result": None,
    }

    if not is_cacheable(task):
        return updated

    cache_key = CacheKeyBuilder.build_from_query(task, state["user_query"])
    if cache_key is None:
        logger.info("CACHE MISS\ntask=%s\nkey=<unavailable>", task)
        return updated

    cached_result = _cache_service.get(cache_key)
    updated["cache_key"] = cache_key

    if cached_result is None:
        logger.info("CACHE MISS\ntask=%s\nkey=%s", task, cache_key)
        return updated

    logger.info("CACHE HIT\ntask=%s\nkey=%s", task, cache_key)
    domain = state.get("domain", "logistics")
    agent_response = json.dumps(
        {
            "agent": _agent_name_for_domain(domain),
            "status": "complete",
            "cached": True,
            "result": cached_result,
        },
        indent=2,
        default=str,
    )
    return {
        **updated,
        "cache_hit": True,
        "cached_result": cached_result,
        "agent_response": agent_response,
    }


def store_cache(state: AgentState) -> AgentState:
    """Store business results after a successful agent execution."""
    task = state.get("task", "")
    cache_key = state.get("cache_key")

    if state.get("cache_hit") or not is_cacheable(task) or not cache_key:
        return state

    try:
        payload = json.loads(state.get("agent_response") or "{}")
    except json.JSONDecodeError:
        return state

    if not isinstance(payload, dict):
        return state

    if payload.get("status") != "complete":
        return state

    business_result = extract_business_result(payload)
    if business_result is None:
        return state

    ttl = ttl_for_task(task)
    if ttl is None:
        return state

    _cache_service.set(cache_key, business_result, ttl)
    logger.info("CACHE STORE\ntask=%s\nttl=%s", task, ttl)
    return state
