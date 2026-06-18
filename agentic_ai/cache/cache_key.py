"""Deterministic cache key generation and query normalization.

Keys embed the role and a role-aware user scope so isolation is enforced at the
key level. The security model (Phase 3):

- COURIER: scope is the authenticated_user_id -> per-courier isolation; one
  courier can never read another courier's cache.
- ADMIN / LOGISTICS / INVENTORY: scope is a shared sentinel -> entries are shared
  across users of the same role (role-level cache), but never across roles.

The role is always part of the key, so cross-role cache sharing is impossible.
The normalized query is hashed (SHA-256) to keep keys fixed-length and free of
raw user text.
"""

from __future__ import annotations

import hashlib
import re

from cache.ttl_config import CACHE_KEY_PREFIX, CACHE_VERSION

_WHITESPACE = re.compile(r"\s+")

_COURIER_ROLE = "COURIER"
_ROLE_SHARED_SCOPE = "_role_shared_"


def normalize_query(query: str) -> str:
    """Normalize a query for cache matching: lowercase, trim, collapse whitespace."""
    collapsed = _WHITESPACE.sub(" ", (query or "").strip())
    return collapsed.lower()


def _query_digest(normalized_query: str) -> str:
    return hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()


def _role_scope(user_id: str, role_part: str) -> str:
    """Per-courier isolation; role-level sharing for every other role."""
    if role_part == _COURIER_ROLE:
        return str(user_id).strip() if user_id else "anon"
    return _ROLE_SHARED_SCOPE


def build_cache_key(query: str, user_id: str, role: str) -> str:
    """Build a deterministic, role-scoped cache key.

    Format: ``<prefix>:v<version>:<ROLE>:<scope>:<sha256(normalized_query)>`` where
    ``scope`` is the user id for COURIER and a shared sentinel for other roles.
    """
    normalized = normalize_query(query)
    role_part = (str(role).strip().upper() if role else "ANON")
    scope = _role_scope(user_id, role_part)
    return f"{CACHE_KEY_PREFIX}:v{CACHE_VERSION}:{role_part}:{scope}:{_query_digest(normalized)}"
