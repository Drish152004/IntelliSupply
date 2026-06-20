"""Deterministic regex entity extraction for the logistics domain.

Only logistics queries reach entity extraction. Inventory executes via NL-SQL
and bypasses extraction entirely (NL-SQL consumes the raw user query and never
uses extracted entities), so this module no longer carries inventory patterns.
Keeping extraction logistics-only also guarantees inventory entities can never
influence orchestration decisions.

``EntityExtractor.extract`` produces, for the logistics domain only:

    order_id, courier_name, hub_name, from_hub, to_hub, city_name, delivery_day
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

# --- Domain identifiers ---------------------------------------------------

LOGISTICS_DOMAIN = "logistics"


# --- Shared helpers -------------------------------------------------------


@dataclass(frozen=True)
class _EntityMatch:
    value: str
    score: int
    start: int


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _best_match(user_query: str, patterns: list[re.Pattern[str]]) -> _EntityMatch | None:
    """Return the highest-priority regex match (earlier patterns win ties)."""
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


# Identifier fields stored lowercase to match GraphDB-stored IDs (e.g. "sh-b-000").
# Text entities (courier_name, city_name, hub_name) are intentionally excluded.
_LOWERCASE_ID_FIELDS: frozenset[str] = frozenset({
    "order_id",
    "courier_id",
    "hub_id",
})


def _lowercase_identifier_fields(entities: dict[str, str]) -> None:
    """Lowercase identifier values in place so lookups match stored IDs."""
    for field in _LOWERCASE_ID_FIELDS:
        value = entities.get(field)
        if value:
            entities[field] = value.lower()


# --- Hub (shared by both domains) -----------------------------------------

_HUB_NAME_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bhub[\s#:_-]*(\d+)\b", re.I),
    re.compile(r"\bHub_(\d+)\b"),
]


def _extract_hub_name(user_query: str) -> str | None:
    """Extract a single hub reference and normalize to ``Hub N``."""
    match = _best_match(user_query, _HUB_NAME_PATTERNS)
    if not match:
        return None
    return f"Hub {int(match.value)}"


# --- Logistics: order_id --------------------------------------------------

# Self-identifying logistics order IDs (e.g. sh-b-000, cq-b-002): two letters,
# a single-letter segment, then a numeric segment.
_DIRECT_LOGISTICS_ID = r"[A-Za-z]{2}-[A-Za-z]-\d{2,4}"

# Hyphenated logistics IDs, ORD-prefixed IDs, or bare tokens (min length 3).
_LOGISTICS_ORDER_ID = (
    r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+|"
    r"ORD[-_]?\d+[A-Za-z0-9-]*|"
    r"[A-Za-z0-9]{3,}"
)

# Hyphenated / ORD-prefixed IDs only — used with logistics-context prefixes.
_CONTEXT_LOGISTICS_ORDER_ID = (
    r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+|"
    r"ORD[-_]?\d+[A-Za-z0-9-]*"
)

_ORDER_ID_PATTERNS: list[re.Pattern[str]] = [
    re.compile(rf"\b({_DIRECT_LOGISTICS_ID})\b", re.I),
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
]

# Command/context words that must never be captured as an order id.
_ORDER_ID_STOP_WORDS: frozenset[str] = frozenset({
    "ID",
    "ORDER",
    "ORD",
    "STATUS",
    "ROUTE",
    "TRACKING",
    "TRACK",
    "ETA",
    "DELIVERY",
    "DETAILS",
    "DETAIL",
    "INFO",
    "LOOKUP",
    "NUMBER",
    "THE",
    "FOR",
    "OF",
    "IS",
    "WHERE",
    "SHIPMENT",
})


def _normalize_order_id(value: str) -> str:
    cleaned = _normalize_whitespace(value).lower()
    if cleaned.startswith("ord-"):
        return cleaned
    if re.fullmatch(r"ord[a-z0-9-]+", cleaned):
        return cleaned
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", cleaned):
        return cleaned
    if re.fullmatch(r"[a-z0-9-]+", cleaned) and not cleaned.startswith("ord"):
        return f"ord{cleaned}" if cleaned.isalnum() and len(cleaned) >= 3 else cleaned
    return cleaned


def _extract_order_id(user_query: str) -> str | None:
    match = _best_match(user_query, _ORDER_ID_PATTERNS)
    if not match:
        return None
    raw = _normalize_whitespace(match.value)
    if raw.upper() in _ORDER_ID_STOP_WORDS:
        return None
    value = _normalize_order_id(raw)
    if not value or value.upper() in _ORDER_ID_STOP_WORDS:
        return None
    return value


# --- Logistics: courier_name (names only, never courier IDs) ---------------

_COURIER_NUMERIC_REF = re.compile(r"\bcourier[\s#:_-]+(\d+)\b", re.I)
_COURIER_NAMED_REF = re.compile(
    r"\bcourier[\s#:_-]+([A-Za-z][A-Za-z0-9]*(?:\s+[A-Za-z][A-Za-z0-9]+)?)\b",
    re.I,
)

_COURIER_NAME_STOP_WORDS: frozenset[str] = frozenset({
    "id",
    "name",
    "names",
    "status",
    "route",
    "routes",
    "order",
    "orders",
    "delivery",
    "deliveries",
    "workload",
    "info",
    "details",
    "detail",
    "number",
    "stop",
    "stops",
    "eta",
    "is",
    "for",
    "of",
    "the",
    "assigned",
})

_COURIER_NAME_PATTERNS: list[re.Pattern[str]] = [
    _COURIER_NUMERIC_REF,
    _COURIER_NAMED_REF,
]


def _extract_courier_name(user_query: str) -> dict[str, str]:
    """Extract a courier *name* (e.g. "Courier 1", "John"). Never a courier id."""
    numeric = _COURIER_NUMERIC_REF.search(user_query)
    if numeric:
        return {"courier_name": f"Courier {int(numeric.group(1))}"}

    named = _COURIER_NAMED_REF.search(user_query)
    if named:
        name = _normalize_whitespace(named.group(1))
        if name.lower() not in _COURIER_NAME_STOP_WORDS:
            return {"courier_name": name}
    return {}


def has_courier_entity(entities: dict[str, str]) -> bool:
    """Return True when entities contain any unresolved or resolved courier reference."""
    return bool(
        entities.get("courier_id")
        or entities.get("courier_reference")
        or entities.get("courier_name")
    )


# --- Logistics: hub_name + directional from_hub/to_hub --------------------

# Precise, hub-prefixed directional patterns only (no broad "from <word>"
# matches) so a logistics query can never bind an arbitrary token as a hub.
_FROM_HUB_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bfrom\s+hub[\s#:_-]*(\d+)\b", re.I),
    re.compile(r"\bbetween\s+hub[\s#:_-]*(\d+)\s+and\s+hub", re.I),
]
_TO_HUB_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bto\s+hub[\s#:_-]*(\d+)\b", re.I),
    re.compile(r"\bbetween\s+hub[\s#:_-]*\d+\s+and\s+hub[\s#:_-]*(\d+)\b", re.I),
]


def _extract_logistics_hubs(user_query: str) -> dict[str, str]:
    """Return directional from/to hubs when both are present, else a single hub_name."""
    from_match = _best_match(user_query, _FROM_HUB_PATTERNS)
    to_match = _best_match(user_query, _TO_HUB_PATTERNS)
    if from_match and to_match:
        return {
            "from_hub": str(int(from_match.value)),
            "to_hub": str(int(to_match.value)),
        }

    hub_name = _extract_hub_name(user_query)
    if hub_name:
        return {"hub_name": hub_name}
    return {}


# --- Logistics: city_name (fixed supported set) ---------------------------

LOGISTICS_CITIES: dict[str, str] = {
    "shanghai": "Shanghai",
    "yantai": "Yantai",
    "beijing": "Beijing",
    "shenzhen": "Shenzhen",
    "guangzhou": "Guangzhou",
}

_CITY_ALTERNATION = "|".join(sorted(LOGISTICS_CITIES, key=len, reverse=True))
_CITY_PATTERN = re.compile(rf"\b({_CITY_ALTERNATION})\b", re.I)


def _extract_city_name(user_query: str) -> str | None:
    match = _CITY_PATTERN.search(user_query)
    if not match:
        return None
    return LOGISTICS_CITIES[match.group(1).lower()]


# --- Logistics: delivery_day (all formats -> YYYY-MM-DD) ------------------

_MONTH_TOKEN = (
    r"january|february|march|april|may|june|july|august|"
    r"september|october|november|december|"
    r"jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"
)

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

# 2026-06-21
_ISO_DELIVERY_DAY = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
# 21/06/2026 or 21-06-2026 (day-first, matching IntelliSupply locale)
_NUMERIC_DMY_DELIVERY = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b")
# 21 June 2026 / 21st June 2026
_DAY_MONTH_YEAR_DELIVERY = re.compile(
    rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH_TOKEN})\s+(\d{{4}})\b",
    re.I,
)
# June 21 2026 / June 21, 2026
_MONTH_DAY_YEAR_DELIVERY = re.compile(
    rf"\b({_MONTH_TOKEN})\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b",
    re.I,
)
# 21 June / 21st June (year inferred from reference date)
_DAY_MONTH_DELIVERY = re.compile(
    rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH_TOKEN})\b",
    re.I,
)
# June 21 (year inferred from reference date)
_MONTH_DAY_DELIVERY = re.compile(
    rf"\b({_MONTH_TOKEN})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b",
    re.I,
)
_RELATIVE_DELIVERY_DAY = re.compile(r"\b(today|tomorrow|yesterday)\b", re.I)


def _month_number(token: str) -> int | None:
    return _MONTH_TO_NUMBER.get(token.strip().lower())


def _canonical_delivery_day(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def _extract_delivery_day(
    user_query: str,
    *,
    reference: date | None = None,
) -> str | None:
    """Extract a delivery day in any supported format and normalize to YYYY-MM-DD."""
    ref = reference or date.today()

    iso = _ISO_DELIVERY_DAY.search(user_query)
    if iso:
        canonical = _canonical_delivery_day(
            int(iso.group(1)), int(iso.group(2)), int(iso.group(3))
        )
        if canonical:
            return canonical

    numeric = _NUMERIC_DMY_DELIVERY.search(user_query)
    if numeric:
        canonical = _canonical_delivery_day(
            int(numeric.group(3)), int(numeric.group(2)), int(numeric.group(1))
        )
        if canonical:
            return canonical

    day_month_year = _DAY_MONTH_YEAR_DELIVERY.search(user_query)
    if day_month_year:
        month = _month_number(day_month_year.group(2))
        if month is not None:
            canonical = _canonical_delivery_day(
                int(day_month_year.group(3)), month, int(day_month_year.group(1))
            )
            if canonical:
                return canonical

    month_day_year = _MONTH_DAY_YEAR_DELIVERY.search(user_query)
    if month_day_year:
        month = _month_number(month_day_year.group(1))
        if month is not None:
            canonical = _canonical_delivery_day(
                int(month_day_year.group(3)), month, int(month_day_year.group(2))
            )
            if canonical:
                return canonical

    day_month = _DAY_MONTH_DELIVERY.search(user_query)
    if day_month:
        month = _month_number(day_month.group(2))
        if month is not None:
            canonical = _canonical_delivery_day(ref.year, month, int(day_month.group(1)))
            if canonical:
                return canonical

    month_day = _MONTH_DAY_DELIVERY.search(user_query)
    if month_day:
        month = _month_number(month_day.group(1))
        if month is not None:
            canonical = _canonical_delivery_day(ref.year, month, int(month_day.group(2)))
            if canonical:
                return canonical

    relative = _RELATIVE_DELIVERY_DAY.search(user_query)
    if relative:
        token = relative.group(1).lower()
        if token == "today":
            return ref.isoformat()
        if token == "tomorrow":
            return (ref + timedelta(days=1)).isoformat()
        if token == "yesterday":
            return (ref - timedelta(days=1)).isoformat()

    return None


# Pattern set exposed for the logistics domain. ``courier_name`` and
# ``delivery_day`` are produced by dedicated helpers (stop-word filtering and
# multi-format normalization respectively); the lists document their drivers.
LOGISTICS_ENTITY_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "order_id": list(_ORDER_ID_PATTERNS),
    "courier_name": list(_COURIER_NAME_PATTERNS),
    "hub_name": list(_HUB_NAME_PATTERNS),
    "from_hub": list(_FROM_HUB_PATTERNS),
    "to_hub": list(_TO_HUB_PATTERNS),
    "city_name": [_CITY_PATTERN],
    "delivery_day": [
        _ISO_DELIVERY_DAY,
        _NUMERIC_DMY_DELIVERY,
        _DAY_MONTH_YEAR_DELIVERY,
        _MONTH_DAY_YEAR_DELIVERY,
        _DAY_MONTH_DELIVERY,
        _MONTH_DAY_DELIVERY,
        _RELATIVE_DELIVERY_DAY,
    ],
}


# --- Public extractor -----------------------------------------------------


class EntityExtractor:
    """Logistics graph-lookup entity extraction.

    Inventory bypasses extraction entirely, so extraction only runs for the
    logistics domain. The ``domain`` argument is retained as a defensive guard:
    any non-logistics value yields no entities, guaranteeing that a non-logistics
    query can never produce logistics entities.
    """

    @staticmethod
    def extract(user_query: str, domain: str = LOGISTICS_DOMAIN) -> dict[str, str]:
        """Return logistics entities. Non-logistics domains yield ``{}``."""
        normalized_domain = (domain or "").strip().lower()
        if normalized_domain == LOGISTICS_DOMAIN:
            return EntityExtractor._extract_logistics(user_query)
        return {}

    @staticmethod
    def _extract_logistics(user_query: str) -> dict[str, str]:
        entities: dict[str, str] = {}

        order_id = _extract_order_id(user_query)
        if order_id:
            entities["order_id"] = order_id

        entities.update(_extract_courier_name(user_query))
        entities.update(_extract_logistics_hubs(user_query))

        city_name = _extract_city_name(user_query)
        if city_name:
            entities["city_name"] = city_name

        delivery_day = _extract_delivery_day(user_query)
        if delivery_day:
            entities["delivery_day"] = delivery_day

        _lowercase_identifier_fields(entities)
        return entities
