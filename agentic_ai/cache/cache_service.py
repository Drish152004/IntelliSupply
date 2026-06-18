"""Low-level cache CRUD over Redis.

JSON-only serialization (never pickle). Every operation is fail-open: any Redis
or serialization error is swallowed and reported as a cache miss / no-op so cache
problems can never raise into orchestration.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from cache.redis_client import get_client

logger = logging.getLogger(__name__)


def get(key: str) -> dict | None:
    """Return the JSON-decoded value for ``key``, or ``None`` on miss/error."""
    client = get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:  # noqa: BLE001 - degrade to miss on any error
        logger.warning("semantic_cache_error get failed key=%s err=%s", key, exc)
        return None


def set(key: str, value: dict, ttl: int) -> bool:
    """JSON-encode ``value`` and store it under ``key`` with a TTL (seconds)."""
    client = get_client()
    if client is None:
        return False
    try:
        payload = json.dumps(value, default=str)
        client.set(key, payload, ex=ttl)
        return True
    except Exception as exc:  # noqa: BLE001 - never raise into callers
        logger.warning("semantic_cache_error set failed key=%s err=%s", key, exc)
        return False


def delete(key: str) -> bool:
    """Delete ``key``. Returns True when an entry was removed."""
    client = get_client()
    if client is None:
        return False
    try:
        return bool(client.delete(key))
    except Exception as exc:  # noqa: BLE001
        logger.warning("semantic_cache_error delete failed key=%s err=%s", key, exc)
        return False


def exists(key: str) -> bool:
    """Return True when ``key`` is present and live."""
    client = get_client()
    if client is None:
        return False
    try:
        return bool(client.exists(key))
    except Exception as exc:  # noqa: BLE001
        logger.warning("semantic_cache_error exists failed key=%s err=%s", key, exc)
        return False
