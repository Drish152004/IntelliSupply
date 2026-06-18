"""Singleton Redis connection for the semantic cache.

Connection construction is lazy and fail-safe: ``get_client`` never raises and
returns ``None`` when Redis is unavailable or the ``redis`` package is missing.
Per-operation errors are handled in ``cache_service``; this module only owns the
client lifecycle and a connectivity ``health_check``.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from cache.ttl_config import redis_settings

logger = logging.getLogger(__name__)

try:  # redis is an optional dependency; absence must not break imports.
    import redis as _redis
except ImportError:  # pragma: no cover - exercised only when redis is absent
    _redis = None

_client: Any | None = None


def _build_client() -> Any | None:
    settings = redis_settings()
    common = {
        "decode_responses": True,
        "socket_timeout": settings["socket_timeout"],
        "socket_connect_timeout": settings["socket_connect_timeout"],
    }
    if settings["url"]:
        return _redis.Redis.from_url(settings["url"], **common)
    return _redis.Redis(
        host=settings["host"],
        port=settings["port"],
        db=settings["db"],
        password=settings["password"],
        **common,
    )


def get_client() -> Any | None:
    """Return a process-wide Redis client, or ``None`` if unavailable.

    Construction does no network I/O (redis-py connects lazily on first command),
    so this is cheap and self-heals: if a previous build failed, the next call
    retries. Never raises.
    """
    global _client
    if _client is not None:
        return _client
    if _redis is None:
        logger.warning("semantic_cache_error redis package not installed")
        return None
    try:
        _client = _build_client()
        return _client
    except Exception as exc:  # noqa: BLE001 - fail open on any construction error
        logger.warning("semantic_cache_error client construction failed: %s", exc)
        return None


def health_check() -> dict:
    """Report cache backend availability and round-trip latency.

    Returns a dict with ``available`` (redis installed + client built),
    ``connected`` (PING succeeded), ``latency_ms`` and ``error``.
    """
    if _redis is None:
        return {
            "available": False,
            "connected": False,
            "latency_ms": None,
            "error": "redis package not installed",
        }

    client = get_client()
    if client is None:
        return {
            "available": False,
            "connected": False,
            "latency_ms": None,
            "error": "client unavailable",
        }

    try:
        start = time.perf_counter()
        client.ping()
        latency_ms = round((time.perf_counter() - start) * 1000, 3)
        return {
            "available": True,
            "connected": True,
            "latency_ms": latency_ms,
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 - health check must never raise
        return {
            "available": True,
            "connected": False,
            "latency_ms": None,
            "error": str(exc),
        }


def reset_client() -> None:
    """Drop the cached client (test/maintenance helper; forces a rebuild)."""
    global _client
    _client = None
