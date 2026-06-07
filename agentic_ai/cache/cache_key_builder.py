"""Deterministic cache key generation from task and normalized entities."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

# At least one of these entity groups must be present for a cacheable lookup.
TASK_ENTITY_REQUIREMENTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "eta_lookup": (("order_id",), ("shipment_id",)),
    "shipment_lookup": (("shipment_id",),),
    "courier_lookup": (("courier_id",),),
    "inventory_nlsql": (("hub_id",), ("product",), ("city",)),
    "demand_forecast": (("region",), ("city",)),
}

_ENTITY_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "order_id": [
        re.compile(r"\b(?:order|ord)[\s#:_-]*([A-Za-z0-9]+)\b", re.I),
        re.compile(r"\bO(\d+)\b"),
    ],
    "shipment_id": [
        re.compile(r"\b(?:shipment|sh)[\s#:_-]*([A-Za-z0-9]+)\b", re.I),
    ],
    "courier_id": [
        re.compile(r"\bcourier[\s#:_-]*(\d+)\b", re.I),
    ],
    "hub_id": [
        re.compile(r"\bhub[\s#:_-]*([A-Za-z0-9]+)\b", re.I),
    ],
    "product": [
        re.compile(
            r"\b(?:product|item|sku)[\s#:_-]*([A-Za-z0-9][A-Za-z0-9\s-]{0,40})\b",
            re.I,
        ),
        re.compile(
            r"\b(laptops?|iphones?|macbooks?|airpods?|tablets?)\b",
            re.I,
        ),
    ],
    "city": [
        re.compile(r"\bin\s+([A-Za-z][A-Za-z\s-]{1,30})\b", re.I),
        re.compile(r"\b(?:city|warehouse)\s+([A-Za-z][A-Za-z\s-]{1,30})\b", re.I),
    ],
    "region": [
        re.compile(r"\b(?:region|area)\s+([A-Za-z0-9][A-Za-z0-9\s-]{0,30})\b", re.I),
        re.compile(
            r"\b(?:demand|deliveries|forecast)(?:\s+\w+){0,3}\s+(?:in|for)\s+"
            r"([A-Za-z][A-Za-z\s-]{1,30})\b",
            re.I,
        ),
    ],
}


def _normalize_entity_value(value: str) -> str:
    cleaned = value.strip().lower()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned.upper()


def _entities_for_task(task: str, entities: dict[str, str]) -> dict[str, str]:
    """Keep only entity types relevant to the cache key for this task."""
    allowed = TASK_ENTITY_REQUIREMENTS.get(task)
    if not allowed:
        return {}
    allowed_keys = {key for group in allowed for key in group}
    return {key: entities[key] for key in allowed_keys if key in entities}


class CacheKeyBuilder:
    """Build deterministic cache keys from task and normalized entities."""

    @staticmethod
    def extract_entities(user_query: str) -> dict[str, str]:
        """Extract normalized entity identifiers from natural language."""
        entities: dict[str, str] = {}
        for entity_name, patterns in _ENTITY_PATTERNS.items():
            for pattern in patterns:
                match = pattern.search(user_query)
                if match:
                    entities[entity_name] = _normalize_entity_value(match.group(1))
                    break
        return entities

    @staticmethod
    def has_required_entities(task: str, entities: dict[str, str]) -> bool:
        """Return True when enough entities exist to build a cache key."""
        scoped = _entities_for_task(task, entities)
        requirements = TASK_ENTITY_REQUIREMENTS.get(task)
        if not requirements:
            return False
        return any(all(entity in scoped for entity in group) for group in requirements)

    @staticmethod
    def build(task: str, entities: dict[str, str]) -> str | None:
        """
        Build a deterministic cache key from task and entities.

        Returns None when required entities are missing.
        """
        scoped = _entities_for_task(task, entities)
        if not CacheKeyBuilder.has_required_entities(task, entities):
            return None

        payload: dict[str, Any] = {"task": task}
        for key in sorted(scoped):
            payload[key] = scoped[key]

        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        return f"{task}:{digest}"

    @staticmethod
    def build_from_query(task: str, user_query: str) -> str | None:
        """Extract entities from a query and build a cache key."""
        entities = CacheKeyBuilder.extract_entities(user_query)
        return CacheKeyBuilder.build(task, entities)
