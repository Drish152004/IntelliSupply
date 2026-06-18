"""Public semantic cache API (Phase 2: exact normalized-query matching).

This is the only module the orchestrator will import when integration begins.
For now it performs exact matching on the normalized query -- no embeddings, no
vector search, no similarity. The public surface is stable so a later phase can
swap the internal match strategy without changing call sites.

All functions are fail-open: a Redis outage degrades to a cache miss / no-op and
never raises into orchestration.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from cache import cache_service
from cache.cache_key import build_cache_key, normalize_query
from cache.redis_client import health_check as _redis_health_check
from cache.ttl_config import CACHE_VERSION, DEFAULT_CACHE_TTL, is_cache_enabled

logger = logging.getLogger(__name__)


def semantic_lookup(query: str, user_id: str, role: str) -> Any | None:
    """Return the cached response for an exact normalized-query match, else None."""
    if not is_cache_enabled():
        return None

    key = build_cache_key(query, user_id, role)
    entry = cache_service.get(key)
    if not entry:
        logger.info("semantic_cache_miss key=%s", key)
        return None

    logger.info("semantic_cache_hit key=%s", key)
    return entry.get("response")


def semantic_store(
    query: str,
    response: Any,
    user_id: str,
    role: str,
    *,
    ttl: int = DEFAULT_CACHE_TTL,
) -> bool:
    """Store a response under the role-scoped normalized-query key. Returns success."""
    if not is_cache_enabled():
        return False

    key = build_cache_key(query, user_id, role)
    entry = {
        "query": normalize_query(query),
        "response": response,
        "authenticated_user_id": user_id,
        "user_role": role,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "cache_version": CACHE_VERSION,
    }

    stored = cache_service.set(key, entry, ttl)
    if stored:
        logger.info("semantic_cache_store key=%s ttl=%s", key, ttl)
    return stored


def semantic_invalidate(query: str, user_id: str, role: str) -> bool:
    """Remove the cache entry for an exact normalized-query match. Returns True if removed."""
    key = build_cache_key(query, user_id, role)
    removed = cache_service.delete(key)
    if removed:
        logger.info("semantic_cache_invalidate key=%s", key)
    return removed


def health_check() -> dict:
    """Report cache backend health (delegates to the Redis client)."""
    return _redis_health_check()
