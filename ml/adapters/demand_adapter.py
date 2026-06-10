"""Adapt Context Resolver demand payloads to Hugging Face feature records."""

from __future__ import annotations

from typing import Any

from ml.validators import PayloadValidationError


def adapt_demand_payload(context_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract HF-compatible feature records from a demand_forecast payload."""
    records = context_payload.get("records")
    if records is None:
        raise PayloadValidationError(
            "demand_forecast requires 'records': a list of HF feature rows "
            "(city, region_id, lags, rolling stats, etc.)."
        )
    if not isinstance(records, list) or not records:
        raise PayloadValidationError("records must be a non-empty list")

    normalized: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise PayloadValidationError(f"records[{index}] must be an object")
        normalized.append(dict(record))
    return normalized
