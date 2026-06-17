"""Canonical self-scoped detection and courier binding for entity extraction."""

from __future__ import annotations

import re

# Substrings that mark a query as referring to the authenticated user's resources.
SELF_SCOPED_PATTERNS: tuple[str, ...] = (
    "my route",
    "my shipments",
    "my shipment",
    "my eta",
    "my next stop",
    "next stop",
    "assigned to me",
    "to me",
    "for me",
)

_MY_PATTERN = re.compile(r"\b(?:my|mine)\b", re.I)


def is_self_scoped_query(user_query: str) -> bool:
    """Return True when the query uses first-person or courier-context phrasing."""
    q = user_query.lower()
    if any(phrase in q for phrase in SELF_SCOPED_PATTERNS):
        return True
    return bool(_MY_PATTERN.search(q))


def apply_self_scoped_entities(
    *,
    entities: dict[str, str],
    user_query: str,
    user_role: str | None,
    session: dict | None,
) -> dict[str, str]:
    """
    Mark self-scoped queries and bind session courier identity when appropriate.

    Intended to be called only from entity_extraction_node.
    """
    resolved = dict(entities)
    if is_self_scoped_query(user_query):
        resolved["self_scoped"] = "true"

    bound = (session or {}).get("courier_id")
    if resolved.get("self_scoped") == "true" and bound and "courier_id" not in resolved:
        resolved["courier_id"] = str(bound)

    return resolved
