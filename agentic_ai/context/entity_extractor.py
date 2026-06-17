"""Deterministic regex-based entity extraction for graph and context resolution."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

_CITY_NAME = r"[A-Za-z][A-Za-z-]+(?:\s+[A-Za-z][A-Za-z-]+)?"
_CITY_END = (
    r"(?=\s+for\s+(?:next\s+)?\d+\s+(?:day|days|week|weeks)\b|\s*$|\s*,)"
)

_ORDER_ID_STOP_WORDS = frozenset({"ID", "ORDER", "ORD"})

# Hyphenated logistics IDs (CQ-B-002) or plain tokens with min length 3 (excludes "id").
_LOGISTICS_ORDER_ID = (
    r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+|"
    r"ORD[-_]?\d+[A-Za-z0-9-]*|"
    r"[A-Za-z0-9]{3,}"
)

# Hyphenated / ORD-prefixed IDs only — used with logistics-context prefixes (no bare tokens).
_CONTEXT_LOGISTICS_ORDER_ID = (
    r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+|"
    r"ORD[-_]?\d+[A-Za-z0-9-]*"
)

_ENTITY_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "order_id": [
        re.compile(r"\b(ORD[-_]?\d+[A-Za-z0-9-]*)\b", re.I),
        re.compile(
            rf"\b(?:order|ord)(?:\s+id)?[\s#:_-]+({_LOGISTICS_ORDER_ID})\b",
            re.I,
        ),
        re.compile(
            rf"\b(?:"
            rf"where\s+is|"
            rf"(?:route|shipment|status|track(?:ing)?|eta|delivery)(?:\s+(?:for|of))?|"
            rf"order(?:\s+(?:for|of))?"
            rf")\s+({_CONTEXT_LOGISTICS_ORDER_ID})\b",
            re.I,
        ),
    ],
    "shipment_id": [
        re.compile(r"\b(SH\d+[A-Za-z0-9-]*)\b", re.I),
        re.compile(r"\bshipment[\s#:_-]+([A-Za-z0-9-]{3,})\b", re.I),
        re.compile(r"\b(ord-[A-Za-z0-9-]+)\b", re.I),
    ],
    "courier_id": [
        re.compile(r"\b(C\d+)\b", re.I),
        re.compile(r"\bcourier[\s#:_-]*([A-Za-z0-9]+)\b", re.I),
    ],
    "hub_id": [
        re.compile(r"\bhub[\s#:_-]*(\d+)\b", re.I),
        re.compile(r"\bHub_(\d+)\b"),
    ],
    "from_hub": [
        re.compile(r"\bfrom\s+(?:hub[\s#:_-]*)?(\d+)\b", re.I),
        re.compile(r"\bbetween\s+hub[\s#:_-]*(\d+)\s+and\s+hub", re.I),
        re.compile(r"\bfrom\s+([A-Za-z][A-Za-z0-9_]*)\b", re.I),
    ],
    "to_hub": [
        re.compile(r"\bto\s+(?:hub[\s#:_-]*)?(\d+)\b", re.I),
        re.compile(r"\bbetween\s+hub[\s#:_-]*\d+\s+and\s+hub[\s#:_-]*(\d+)\b", re.I),
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
    "sku_id": [
        re.compile(r"\b(?:sku|stock\s+keeping\s+unit)[\s#:_-]*([A-Za-z0-9-]+)\b", re.I),
        re.compile(r"\b(SKU[A-Za-z0-9-]+)\b", re.I),
    ],
    "warehouse_id": [
        re.compile(r"\b(?:warehouse|wh)\b[\s#:_-]+([A-Za-z0-9-]+)\b", re.I),
    ],
    "product_name": [
        re.compile(
            r"\b(?:product|item|iphone|router|laptop|phone|tablet)\s+"
            r"([A-Za-z0-9][A-Za-z0-9\s\-]+?)(?=\s+(?:in|at|for|stock|units?)\b|\s*$)",
            re.I,
        ),
        re.compile(
            r"\b(?:how many|stock of|units of)\s+([A-Za-z0-9][A-Za-z0-9\s\-]+?)"
            r"(?=\s+(?:in|at|are|do)\b|\s*\?|\s*$)",
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

_CITY_NAME_STOP_WORDS = frozenset({
    "list",
    "all",
    "with",
    "show",
    "get",
    "which",
    "enumerate",
    "names",
    "pls",
    "hubs",
    "hub",
    "cities",
    "city",
})

_MONTH_TOKEN = (
    r"january|february|march|april|may|june|july|august|"
    r"september|october|november|december|"
    r"jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"
)

_ISO_DELIVERY_DAY = re.compile(r"\b(?:on\s+)?(\d{4}-\d{2}-\d{2})\b", re.I)
_MONTH_DAY_DELIVERY = re.compile(
    rf"\b(?:on\s+)?({_MONTH_TOKEN})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b",
    re.I,
)
_DAY_MONTH_DELIVERY = re.compile(
    rf"\b(?:on\s+)?(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH_TOKEN})\b",
    re.I,
)
_RELATIVE_DELIVERY_DAY = re.compile(r"\b(?:on\s+)?(today|tomorrow)\b", re.I)

_MONTH_TO_NUMBER: dict[str, int] = {
    "january": 1,
    "jan": 1,
    "february": 2,
    "feb": 2,
    "march": 3,
    "mar": 3,
    "april": 4,
    "apr": 4,
    "may": 5,
    "june": 6,
    "jun": 6,
    "july": 7,
    "jul": 7,
    "august": 8,
    "aug": 8,
    "september": 9,
    "sep": 9,
    "sept": 9,
    "october": 10,
    "oct": 10,
    "november": 11,
    "nov": 11,
    "december": 12,
    "dec": 12,
}

@dataclass(frozen=True)
class _EntityMatch:
    value: str
    score: int
    start: int


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _normalize_order_id(value: str) -> str:
    cleaned = _normalize_whitespace(value).upper()
    if cleaned in _ORDER_ID_STOP_WORDS:
        return ""
    if cleaned.startswith("ORD-"):
        return cleaned
    if re.fullmatch(r"ORD[A-Z0-9-]+", cleaned):
        return cleaned
    if re.fullmatch(r"[A-Z0-9]+(?:-[A-Z0-9]+)+", cleaned):
        return cleaned
    if re.fullmatch(r"[A-Z0-9-]+", cleaned) and not cleaned.startswith("ORD"):
        return f"ORD{cleaned}" if cleaned.isalnum() and len(cleaned) >= 3 else cleaned
    return cleaned


def _is_valid_order_id(value: str) -> bool:
    if not value:
        return False
    return value.upper() not in _ORDER_ID_STOP_WORDS


def _normalize_last_completed_order(value: str) -> str:
    cleaned = _normalize_whitespace(value)
    if cleaned.upper().startswith("SH"):
        return _normalize_shipment_id(cleaned)
    return _normalize_order_id(cleaned)


def _normalize_shipment_id(value: str) -> str:
    cleaned = _normalize_whitespace(value)
    if cleaned.lower().startswith("sh"):
        return cleaned.upper()
    if cleaned.lower().startswith("ord-"):
        return cleaned.lower()
    return cleaned


def _normalize_courier_id(value: str) -> str:
    cleaned = _normalize_whitespace(value).upper()
    if re.fullmatch(r"\d+", cleaned):
        return f"C{cleaned}"
    if re.fullmatch(r"C\d+", cleaned, re.I):
        return cleaned.upper()
    return cleaned.upper()


def _normalize_hub_ref(value: str) -> str:
    cleaned = _normalize_whitespace(value)
    if cleaned.isdigit():
        return f"Hub_{int(cleaned)}"
    if cleaned.lower().startswith("hub_"):
        parts = cleaned.split("_", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return f"Hub_{int(parts[1])}"
    if cleaned.lower().startswith("hub") and cleaned[3:].isdigit():
        return f"Hub_{int(cleaned[3:])}"
    hub_match = re.search(r"hub[\s#:_-]*(\d+)", cleaned, re.I)
    if hub_match:
        return f"Hub_{int(hub_match.group(1))}"
    return cleaned


def _normalize_sku_id(value: str) -> str:
    cleaned = _normalize_whitespace(value).upper()
    return cleaned if cleaned.startswith("SKU") else f"SKU{cleaned}"


def _normalize_warehouse_id(value: str) -> str:
    return _normalize_whitespace(value).upper()


def _normalize_product_name(value: str) -> str:
    return _normalize_whitespace(value)


def _normalize_city_name(value: str) -> str:
    return _normalize_whitespace(value)


_ENTITY_NORMALIZERS: dict[str, callable] = {
    "order_id": _normalize_order_id,
    "shipment_id": _normalize_shipment_id,
    "courier_id": _normalize_courier_id,
    "hub_id": _normalize_hub_ref,
    "from_hub": _normalize_hub_ref,
    "to_hub": _normalize_hub_ref,
    "city_name": _normalize_city_name,
    "sku_id": _normalize_sku_id,
    "warehouse_id": _normalize_warehouse_id,
    "product_name": _normalize_product_name,
}


def _is_valid_hub_id(value: str) -> bool:
    return bool(re.fullmatch(r"Hub_\d+", value, re.I))


def _is_valid_city_name(value: str) -> bool:
    normalized = value.strip().lower()
    if not normalized or normalized in _CITY_NAME_STOP_WORDS:
        return False
    return bool(re.fullmatch(r"[a-z][a-z-]+(?:\s+[a-z][a-z-]+)?", normalized, re.I))


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


def _canonical_delivery_day(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _month_number(token: str) -> int | None:
    return _MONTH_TO_NUMBER.get(token.strip().lower())


def _extract_delivery_day(
    user_query: str,
    *,
    reference: date | None = None,
) -> str | None:
    """Extract and normalize a delivery day to YYYY-MM-DD."""
    ref = reference or date.today()

    iso_match = _ISO_DELIVERY_DAY.search(user_query)
    if iso_match:
        try:
            return date.fromisoformat(iso_match.group(1)).isoformat()
        except ValueError:
            pass

    month_day_match = _MONTH_DAY_DELIVERY.search(user_query)
    if month_day_match:
        month = _month_number(month_day_match.group(1))
        if month is not None:
            day = int(month_day_match.group(2))
            canonical = _canonical_delivery_day(ref.year, month, day)
            if canonical:
                return canonical

    day_month_match = _DAY_MONTH_DELIVERY.search(user_query)
    if day_month_match:
        month = _month_number(day_month_match.group(2))
        if month is not None:
            day = int(day_month_match.group(1))
            canonical = _canonical_delivery_day(ref.year, month, day)
            if canonical:
                return canonical

    relative_match = _RELATIVE_DELIVERY_DAY.search(user_query)
    if relative_match:
        token = relative_match.group(1).lower()
        if token == "today":
            return ref.isoformat()
        if token == "tomorrow":
            return (ref + timedelta(days=1)).isoformat()

    return None


def _best_match(user_query: str, patterns: list[re.Pattern[str]]) -> _EntityMatch | None:
    best: _EntityMatch | None = None
    total = len(patterns)
    for index, pattern in enumerate(patterns):
        match = pattern.search(user_query)
        if not match:
            continue
        score = total - index
        candidate = _EntityMatch(
            value=match.group(1),
            score=score,
            start=match.start(),
        )
        if best is None or candidate.score > best.score or (
            candidate.score == best.score and candidate.start < best.start
        ):
            best = candidate
    return best


class EntityExtractor:
    """Extract graph lookup entities from natural language queries."""

    @staticmethod
    def extract(user_query: str) -> dict[str, str]:
        """Return extracted entity identifiers keyed by entity type in canonical form."""
        entities: dict[str, str] = {}
        for entity_name, patterns in _ENTITY_PATTERNS.items():
            match = _best_match(user_query, patterns)
            if match:
                normalizer = _ENTITY_NORMALIZERS.get(entity_name, _normalize_whitespace)
                value = normalizer(match.value)
                if entity_name == "hub_id" and not _is_valid_hub_id(value):
                    continue
                if entity_name == "order_id" and not _is_valid_order_id(value):
                    continue
                if entity_name == "city_name" and not _is_valid_city_name(value):
                    continue
                entities[entity_name] = value

        city_horizon_match = _extract_city_horizon(user_query)
        if city_horizon_match:
            city_candidate = _normalize_city_name(city_horizon_match.group(1))
            if _is_valid_city_name(city_candidate):
                entities["city_name"] = city_candidate
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

        if "city_name" in entities and "city" not in entities:
            entities["city"] = entities["city_name"]

        delivery_day = _extract_delivery_day(user_query)
        if delivery_day:
            entities["delivery_day"] = delivery_day

        return entities

    @staticmethod
    def extract_next_stop_position(user_query: str) -> dict[str, str]:
        """Extract position context for next_stop_lookup HITL resume answers."""
        current_stop_patterns = [
            re.compile(
                r"\bcurrent\s+stop\s+(Hub[\s#:_-]*\d+|Hub_\d+)\b",
                re.I,
            ),
            re.compile(r"\b(Hub_?\d+)\b", re.I),
            re.compile(r"\bhub[\s#:_-]*(\d+)\b", re.I),
        ]
        current_match = _best_match(user_query, current_stop_patterns)
        if current_match:
            hub_value = _normalize_hub_ref(current_match.value)
            if _is_valid_hub_id(hub_value):
                return {"current_stop": hub_value}

        completed_order = re.search(
            r"\bcompleted\s+(ORD[-_]?\d+[A-Za-z0-9-]*)\b",
            user_query,
            re.I,
        )
        if completed_order:
            return {
                "last_completed_order": _normalize_last_completed_order(
                    completed_order.group(1),
                ),
            }

        completed_shipment = re.search(
            r"\bcompleted\s+(SH\d+[A-Za-z0-9-]*)\b",
            user_query,
            re.I,
        )
        if completed_shipment:
            return {
                "last_completed_order": _normalize_last_completed_order(
                    completed_shipment.group(1),
                ),
            }

        entities = EntityExtractor.extract(user_query)
        if entities.get("hub_id"):
            return {"current_stop": entities["hub_id"]}

        if entities.get("order_id"):
            return {"last_completed_order": entities["order_id"]}

        if entities.get("shipment_id"):
            return {"last_completed_order": _normalize_last_completed_order(
                entities["shipment_id"],
            )}

        return {}
