"""Result normalization layer between graph execution and answer generation.

This module sits immediately before ``answer_generation`` and reshapes raw
graph rows into a clean, JSON-safe, de-duplicated, and (where obvious) grouped
structure so the answer model receives analyst-ready data instead of raw rows.

Hard guarantee: normalization only RESTRUCTURES existing values. It never
infers, invents, or derives business facts (route status, delivery completion,
courier status, etc.). The caller preserves the original raw result separately,
so this layer only affects the data handed to the answer model.
"""

from __future__ import annotations

import json
import re
from typing import Any

_FENCE_RE = re.compile(r"^```(?:json|cypher|sql)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)


def _clean_value(value: Any) -> Any:
    """Recursively convert a value into a clean, JSON-safe Python value.

    - strips markdown fences from strings
    - parses JSON-looking strings into objects
    - converts datetime-like objects to ISO strings
    - converts any other non-primitive to ``str``
    """
    if value is None or isinstance(value, (int, float, bool)):
        return value

    if isinstance(value, str):
        text = value.strip()
        fenced = _FENCE_RE.match(text)
        if fenced:
            text = fenced.group(1).strip()
        if text[:1] in ("{", "["):
            try:
                return _clean_value(json.loads(text))
            except (json.JSONDecodeError, ValueError):
                return text
        return text

    if isinstance(value, (list, tuple)):
        return [_clean_value(item) for item in value]

    if isinstance(value, dict):
        return {str(key): _clean_value(val) for key, val in value.items()}

    if hasattr(value, "iso_format"):
        try:
            return value.iso_format()
        except Exception:
            pass

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    return str(value)


def _dedupe_preserving_order(rows: list[Any]) -> list[Any]:
    """Remove exact duplicate rows while preserving first-seen ordering."""
    seen: set[str] = set()
    output: list[Any] = []
    for row in rows:
        try:
            fingerprint = json.dumps(row, sort_keys=True, default=str)
        except TypeError:
            fingerprint = str(row)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        output.append(row)
    return output


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _pluralize(name: str) -> str:
    if not name or name.endswith("s"):
        return name
    return f"{name}s"


def _aggregate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse repeated entities into grouped rows (obvious grouping only).

    A column is treated as a grouping KEY when it is scalar and repeats (its
    distinct value count is below the row count). The remaining columns are
    DETAIL columns and are collapsed into lists with a ``<col>_count``.

    Aggregation is skipped unless it actually reduces the row count and leaves
    at least one key column and one detail column. No facts are invented.
    """
    if len(rows) < 2:
        return rows

    keys = list(rows[0].keys())
    key_set = set(keys)
    if any(set(row.keys()) != key_set for row in rows):
        return rows

    scalar_cols = [k for k in keys if all(_is_scalar(row.get(k)) for row in rows)]
    if not scalar_cols:
        return rows

    row_count = len(rows)
    key_cols = [k for k in scalar_cols if len({row.get(k) for row in rows}) < row_count]
    if not key_cols:
        return rows

    detail_cols = [k for k in keys if k not in key_cols]
    if not detail_cols:
        return rows

    groups: dict[tuple, list[dict[str, Any]]] = {}
    group_order: list[tuple] = []
    for row in rows:
        group_key = tuple(row.get(k) for k in key_cols)
        if group_key not in groups:
            groups[group_key] = []
            group_order.append(group_key)
        groups[group_key].append(row)

    if len(group_order) >= row_count:
        return rows

    aggregated: list[dict[str, Any]] = []
    for group_key in group_order:
        members = groups[group_key]
        collapsed: dict[str, Any] = dict(zip(key_cols, group_key))
        for col in detail_cols:
            values = [member.get(col) for member in members]
            plural = _pluralize(col)
            if plural in collapsed or plural in key_set:
                plural = f"{col}_list"
            collapsed[plural] = values
            count_name = f"{col}_count"
            if count_name not in collapsed:
                collapsed[count_name] = len(values)
        aggregated.append(collapsed)
    return aggregated


def normalize_result_for_answer(result: Any) -> dict[str, Any]:
    """Normalize a raw graph result for the answer model.

    Returns ``{"total_records": N, "normalized_rows": [...]}`` where the rows
    are cleaned, de-duplicated, and (when obvious) grouped. Pure restructuring
    only — no business facts are inferred.
    """
    cleaned = _clean_value(result)

    if isinstance(cleaned, list):
        rows = _dedupe_preserving_order(cleaned)
        if rows and all(isinstance(row, dict) for row in rows):
            rows = _aggregate_rows(rows)
        normalized_rows = rows
    elif isinstance(cleaned, dict):
        normalized_rows = [cleaned]
    elif cleaned is None:
        normalized_rows = []
    else:
        normalized_rows = [cleaned]

    return {
        "total_records": len(normalized_rows),
        "normalized_rows": normalized_rows,
    }
