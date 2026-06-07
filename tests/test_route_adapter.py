"""Tests for route context → DeliveryPipeline order adaptation."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.adapters.route_adapter import adapt_route_payload
from ml.validators import PayloadValidationError, validate_route_payload

CONTEXT_PAYLOAD = {
    "order_id": "ord-abc123",
    "lat_wgs84": 30.61,
    "lon_wgs84": 104.01,
    "receipt_lat_wgs84": 30.60,
    "receipt_lon_wgs84": 104.00,
    "city_name": "Shanghai",
    "ds": 318,
    "delivery_day": "Monday",
    "receipt_time": "2026-06-05T12:00:00",
    "typecode": "T1",
    "aoi_id": "7",
}


def test_adapt_route_payload_produces_valid_pipeline_schema() -> None:
    orders = adapt_route_payload(CONTEXT_PAYLOAD)

    assert len(orders) == 1
    order = orders[0]

    assert order["order_id"] == "ord-abc123"
    assert order["lat_wgs84"] == pytest.approx(30.61)
    assert order["lon_wgs84"] == pytest.approx(104.01)
    assert order["receipt_lat_wgs84"] == pytest.approx(30.60)
    assert order["receipt_lon_wgs84"] == pytest.approx(104.00)
    assert order["city_name"] == "Shanghai"
    assert order["ds"] == 318
    assert order["delivery_day"] == "Monday"
    assert order["receipt_time"] == "2026-06-05T12:00:00"
    assert order["typecode"] == "T1"
    assert order["aoi_id"] == "7"

    validate_route_payload(order, schema="pipeline")


def test_adapt_route_payload_preserves_wgs84_without_conversion() -> None:
    orders = adapt_route_payload(CONTEXT_PAYLOAD)
    order = orders[0]

    assert "poi_lat" not in order
    assert "poi_lng" not in order
    assert "model_lat" not in order


def test_adapt_route_payload_coerces_string_ds() -> None:
    payload = {**CONTEXT_PAYLOAD, "ds": "318"}
    order = adapt_route_payload(payload)[0]
    assert order["ds"] == 318
    validate_route_payload(order, schema="pipeline")


def test_adapt_route_payload_rejects_missing_field() -> None:
    incomplete = {k: v for k, v in CONTEXT_PAYLOAD.items() if k != "order_id"}
    with pytest.raises(PayloadValidationError, match="order_id"):
        adapt_route_payload(incomplete)
