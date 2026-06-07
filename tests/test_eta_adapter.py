"""Tests for ETA context → pipeline payload adaptation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.adapters.eta_adapter import adapt_eta_payload
from ml.validators import PayloadValidationError, validate_eta_payload

CONTEXT_PAYLOAD = {
    "delivery_user_id": "C001",
    "from_dipan_id": "42",
    "aoi_id": "7",
    "receipt_lat": 30.6,
    "receipt_lng": 104.0,
    "poi_lat": 30.61,
    "poi_lng": 104.01,
    "receipt_time": "2026-06-05T12:00:00",
}


def test_adapt_eta_payload_produces_valid_pipeline_schema() -> None:
    result = adapt_eta_payload(CONTEXT_PAYLOAD)

    assert result["delivery_user_id"] == "C001"
    assert result["from_dipan_id"] == "42"
    assert result["aoi_id"] == "7"
    assert result["receipt_lat"] == pytest.approx(30.6)
    assert result["receipt_lng"] == pytest.approx(104.0)
    assert result["poi_lat"] == pytest.approx(30.61)
    assert result["poi_lng"] == pytest.approx(104.01)
    assert result["receipt_time"] == "2026-06-05T12:00:00"

    validate_eta_payload(result, schema="pipeline")


def test_adapt_eta_payload_coerces_numeric_ids() -> None:
    payload = {**CONTEXT_PAYLOAD, "from_dipan_id": 42, "aoi_id": 7}
    result = adapt_eta_payload(payload)

    assert result["from_dipan_id"] == "42"
    assert result["aoi_id"] == "7"
    validate_eta_payload(result, schema="pipeline")


def test_adapt_eta_payload_rejects_missing_field() -> None:
    incomplete = {k: v for k, v in CONTEXT_PAYLOAD.items() if k != "receipt_time"}
    with pytest.raises(PayloadValidationError, match="receipt_time"):
        adapt_eta_payload(incomplete)


def test_adapt_eta_payload_rejects_invalid_datetime() -> None:
    bad = {**CONTEXT_PAYLOAD, "receipt_time": "not-a-date"}
    with pytest.raises(PayloadValidationError, match="ISO-8601"):
        adapt_eta_payload(bad)
