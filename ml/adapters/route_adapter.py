"""Adapt Context Resolver route payloads to DeliveryPipeline order inputs."""

from __future__ import annotations

from typing import Any, TypedDict

from ml.validators import normalize_iso_datetime, validate_route_payload


class RouteOrderPayload(TypedDict):
    order_id: str
    lat_wgs84: float
    lon_wgs84: float
    receipt_lat_wgs84: float
    receipt_lon_wgs84: float
    city_name: str
    ds: int
    delivery_day: str
    receipt_time: str
    typecode: str
    aoi_id: str


def _normalize_receipt_time(value: Any) -> str:
    return normalize_iso_datetime(value, "receipt_time")


def adapt_route_payload(context_payload: dict[str, Any]) -> list[RouteOrderPayload]:
    """
    Transform a Context Resolver route_prediction payload into the order list
    expected by DeliveryPipeline.run(orders=...).

    Coordinate conversion is deferred to enrich_order_dict inside the pipeline.
    """
    validate_route_payload(context_payload, schema="context")

    order: RouteOrderPayload = {
        "order_id": str(context_payload["order_id"]).strip(),
        "lat_wgs84": float(context_payload["lat_wgs84"]),
        "lon_wgs84": float(context_payload["lon_wgs84"]),
        "receipt_lat_wgs84": float(context_payload["receipt_lat_wgs84"]),
        "receipt_lon_wgs84": float(context_payload["receipt_lon_wgs84"]),
        "city_name": str(context_payload["city_name"]).strip(),
        "ds": int(context_payload["ds"]),
        "delivery_day": str(context_payload["delivery_day"]).strip(),
        "receipt_time": _normalize_receipt_time(context_payload["receipt_time"]),
        "typecode": str(context_payload["typecode"]).strip(),
        "aoi_id": str(context_payload["aoi_id"]).strip(),
    }

    validate_route_payload(order, schema="pipeline")
    return [order]
