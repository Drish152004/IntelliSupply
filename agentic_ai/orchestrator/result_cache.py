"""Lightweight in-memory exact-result cache for the orchestrator.

This is intentionally simple:
- Process-memory dictionary only (no Redis, no embeddings, no semantic search).
- Keyed on the *fully prepared function call* (function_name + payload + role +
  courier_id), never on the raw user question. This lets normalized variants
  ("Where is ORD123?", "Track ORD123", "Status of ORD123") share one entry.
- Per-courier isolation: courier_id is part of the key, so couriers never share
  cached results.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

CACHE: dict[str, dict[str, Any]] = {}

CACHE_TTL_SECONDS = 60


def make_cache_key(
    *,
    function_name: str,
    payload: dict[str, Any] | None,
    user_role: str | None,
    courier_id: str | None = None,
) -> str:
    """Build a deterministic cache key from the prepared function call.

    The payload is serialized with sorted keys so logically identical payloads
    map to the same key regardless of dict ordering.
    """
    canonical = json.dumps(payload or {}, sort_keys=True, default=str)
    payload_digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:16]
    role_part = (user_role or "anon").strip().upper()
    key = f"{function_name}:{payload_digest}:role_{role_part}"
    if courier_id:
        key = f"{key}:courier_{str(courier_id).strip()}"
    return key


def get_cached_result(cache_key: str) -> Any | None:
    """Return a live cached value, or None on miss/expiry."""
    entry = CACHE.get(cache_key)
    if not entry:
        return None
    if entry["expires_at"] < time.time():
        CACHE.pop(cache_key, None)
        return None
    return entry["value"]


def set_cached_result(
    cache_key: str,
    value: Any,
    ttl_seconds: int = CACHE_TTL_SECONDS,
) -> None:
    """Store a successful structured result with a TTL."""
    CACHE[cache_key] = {
        "value": value,
        "expires_at": time.time() + ttl_seconds,
    }


def clear_cache() -> None:
    """Drop all cached entries (test/maintenance helper)."""
    CACHE.clear()
