"""Deterministic regex-based entity extraction for graph and context resolution."""

from __future__ import annotations

import re

_ENTITY_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "order_id": [
        re.compile(r"\b(?:order|ord)[\s#:_-]*([A-Za-z0-9-]+)\b", re.I),
        re.compile(r"\b(ORD[A-Za-z0-9]+)\b", re.I),
    ],
    "shipment_id": [
        re.compile(r"\b(?:shipment|sh)[\s#:_-]*([A-Za-z0-9-]+)\b", re.I),
    ],
    "courier_id": [
        re.compile(r"\bcourier[\s#:_-]*([A-Za-z0-9]+)\b", re.I),
        re.compile(r"\b(C\d+)\b", re.I),
    ],
    "hub_id": [
        re.compile(r"\bhub[\s#:_-]*([A-Za-z0-9]+)\b", re.I),
    ],
    "from_hub": [
        re.compile(r"\bfrom\s+([A-Za-z][A-Za-z0-9_]*)\b", re.I),
    ],
    "to_hub": [
        re.compile(r"\bto\s+([A-Za-z][A-Za-z0-9_]*)\b", re.I),
    ],
    "city_name": [
        re.compile(r"\bin\s+([A-Za-z][A-Za-z\s-]{1,30})\b", re.I),
        re.compile(r"\b(?:city)\s+([A-Za-z][A-Za-z\s-]{1,30})\b", re.I),
        re.compile(
            r"\b(?:demand|deliveries|forecast)(?:\s+\w+){0,3}\s+(?:in|for)\s+"
            r"([A-Za-z][A-Za-z\s-]{1,30})\b",
            re.I,
        ),
    ],
}

_HORIZON_PATTERN = re.compile(
    r"\b(?:next|for)\s+(\d+)\s+(day|days|week|weeks)\b",
    re.I,
)

_SELF_SCOPED_PATTERN = re.compile(
    r"\b(?:my|mine)\b",
    re.I,
)


def _normalize_entity_value(value: str) -> str:
    cleaned = value.strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


class EntityExtractor:
    """Extract graph lookup entities from natural language queries."""

    @staticmethod
    def extract(user_query: str) -> dict[str, str]:
        """Return extracted entity identifiers keyed by entity type."""
        entities: dict[str, str] = {}
        for entity_name, patterns in _ENTITY_PATTERNS.items():
            for pattern in patterns:
                match = pattern.search(user_query)
                if match:
                    entities[entity_name] = _normalize_entity_value(match.group(1))
                    break

        if _SELF_SCOPED_PATTERN.search(user_query):
            entities["self_scoped"] = "true"

        horizon_match = _HORIZON_PATTERN.search(user_query)
        if horizon_match:
            count = int(horizon_match.group(1))
            unit = horizon_match.group(2).lower()
            if unit.startswith("week"):
                entities["horizon"] = str(count)
                entities["granularity"] = "weekly"
            else:
                entities["horizon"] = str(count)
                entities["granularity"] = "daily"

        if "city_name" in entities and "city" not in entities:
            entities["city"] = entities["city_name"]

        return entities
