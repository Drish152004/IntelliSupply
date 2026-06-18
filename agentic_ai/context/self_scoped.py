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
) -> dict[str, str]:
    """
    Mark self-scoped queries.

    Intended to be called only from entity_extraction_node.

    Courier identity binding for self-scoped queries no longer happens here: it
    is performed in entity resolution from ``bound_courier_id`` (the new courier
    identity model). This function therefore no longer reads logistics_session.
    """
    resolved = dict(entities)
    if is_self_scoped_query(user_query):
        resolved["self_scoped"] = "true"

    return resolved
