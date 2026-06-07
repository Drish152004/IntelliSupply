"""Deterministic regex-based entity extraction for graph and context resolution."""

from __future__ import annotations

import re

_CITY_NAME = r"[A-Za-z][A-Za-z-]+(?:\s+[A-Za-z][A-Za-z-]+)?"
_CITY_END = (
    r"(?=\s+for\s+(?:next\s+)?\d+\s+(?:day|days|week|weeks)\b|\s*$|\s*,)"
)

_ENTITY_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "order_id": [
        re.compile(r"\b(?:order|ord)[\s#:_-]*([A-Za-z0-9-]+)\b", re.I),
        re.compile(r"\b(ORD[A-Za-z0-9]+)\b", re.I),
    ],
    "shipment_id": [
        re.compile(r"\bshipment[\s#:_-]*([A-Za-z0-9-]+)\b", re.I),
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
        re.compile(rf"\bin\s+({_CITY_NAME}){_CITY_END}", re.I),
        re.compile(rf"\b(?:city)\s+({_CITY_NAME}){_CITY_END}", re.I),
        re.compile(
            rf"\b(?:demand|deliveries|forecast)(?:\s+\w+){{0,3}}\s+(?:in|for)\s+"
            rf"({_CITY_NAME}){_CITY_END}",
            re.I,
        ),
    ],
}

_HORIZON_PATTERN = re.compile(
    r"\b(?:next|for)\s+(\d+)\s+(day|days|week|weeks)\b",
    re.I,
)

_CITY_HORIZON_PREFIXED = re.compile(
    rf"\b(?:in|for)\s+({_CITY_NAME})\s+for\s+(?:next\s+)?(\d+)\s+(day|days|week|weeks)\b",
    re.I,
)

_CITY_HORIZON_BARE = re.compile(
    r"\b([A-Za-z][A-Za-z-]+)\s+for\s+(?:next\s+)?(\d+)\s+(day|days|week|weeks)\b",
    re.I,
)

_CITY_HORIZON_STOP_WORDS = frozenset({
    "demand",
    "delivery",
    "deliveries",
    "forecast",
    "next",
    "for",
    "in",
})

_SELF_SCOPED_PATTERN = re.compile(
    r"\b(?:my|mine)\b",
    re.I,
)


def _normalize_entity_value(value: str) -> str:
    cleaned = value.strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _apply_horizon(entities: dict[str, str], count: int, unit: str) -> None:
    if unit.startswith("week"):
        entities["horizon"] = str(count)
        entities["granularity"] = "weekly"
    else:
        entities["horizon"] = str(count)
        entities["granularity"] = "daily"


def _extract_city_horizon(user_query: str) -> re.Match[str] | None:
    prefixed = _CITY_HORIZON_PREFIXED.search(user_query)
    if prefixed:
        return prefixed

    for match in _CITY_HORIZON_BARE.finditer(user_query):
        if match.group(1).lower() not in _CITY_HORIZON_STOP_WORDS:
            return match
    return None


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

        city_horizon_match = _extract_city_horizon(user_query)
        if city_horizon_match:
            entities["city_name"] = _normalize_entity_value(city_horizon_match.group(1))
            _apply_horizon(
                entities,
                int(city_horizon_match.group(2)),
                city_horizon_match.group(3).lower(),
            )
        else:
            horizon_match = _HORIZON_PATTERN.search(user_query)
            if horizon_match:
                _apply_horizon(
                    entities,
                    int(horizon_match.group(1)),
                    horizon_match.group(2).lower(),
                )

        if _SELF_SCOPED_PATTERN.search(user_query):
            entities["self_scoped"] = "true"

        if "city_name" in entities and "city" not in entities:
            entities["city"] = entities["city_name"]

        return entities
