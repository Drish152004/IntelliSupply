"""Centralized configuration for the Redis semantic cache.

All values are environment-driven (loaded once via ``config.env.load_env``) so the
cache can be tuned per environment without code changes. No task-specific TTL logic
lives here yet -- only the generic DEFAULT / SHORT / LONG tiers.
"""

from __future__ import annotations

import os

from config.env import load_env

load_env()

# Bump when the stored payload schema changes; mismatched entries are treated as
# misses so a format change is a safe rolling upgrade.
CACHE_VERSION = 1


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(str(raw).strip())
    except ValueError:
        return default


# TTL tiers (seconds). No per-task mapping yet -- callers pass one of these.
DEFAULT_CACHE_TTL = _int_env("CACHE_TTL_SECONDS", 300)
SHORT_CACHE_TTL = _int_env("CACHE_SHORT_TTL_SECONDS", 60)
LONG_CACHE_TTL = _int_env("CACHE_LONG_TTL_SECONDS", 3600)

# Namespace prefix for every key this module writes.
CACHE_KEY_PREFIX = os.getenv("CACHE_KEY_PREFIX", "iscache")

_TRUTHY = {"1", "true", "yes", "on"}


def is_cache_enabled() -> bool:
    """Master on/off switch. Defaults to enabled; set CACHE_ENABLED=false to disable."""
    return str(os.getenv("CACHE_ENABLED", "true")).strip().lower() in _TRUTHY


def redis_settings() -> dict:
    """Resolve Redis connection settings from the environment.

    REDIS_URL (e.g. ``redis://:pw@host:6379/0``) takes precedence when set;
    otherwise discrete host/port/db/password values are used. Timeouts are kept
    short so a Redis outage degrades to a cache miss quickly rather than stalling
    the caller.
    """
    return {
        "url": os.getenv("REDIS_URL") or None,
        "host": os.getenv("REDIS_HOST", "localhost"),
        "port": _int_env("REDIS_PORT", 6379),
        "db": _int_env("REDIS_DB", 0),
        "password": os.getenv("REDIS_PASSWORD") or None,
        "socket_timeout": _float_env("REDIS_SOCKET_TIMEOUT", 0.5),
        "socket_connect_timeout": _float_env("REDIS_CONNECT_TIMEOUT", 0.5),
    }
