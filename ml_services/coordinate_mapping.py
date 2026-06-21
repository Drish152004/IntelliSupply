"""Coordinate mapping for route/ETA ML models.

Converts real WGS84 coordinates to Web Mercator metres (poi_lat / poi_lng)
used by the route and ETA predictors.
"""

from __future__ import annotations

from math import log, pi, tan
from typing import Any

EARTH_RADIUS_M = 6_378_137.0
MAX_MERCATOR_LAT = 85.05112878


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def wgs84_to_web_mercator(lat: float, lng: float) -> tuple[float, float]:
    """Convert WGS84 degrees to Web Mercator (poi_lng, poi_lat) in metres."""
    lat_clamped = _clamp(lat, -MAX_MERCATOR_LAT, MAX_MERCATOR_LAT)
    poi_lng = EARTH_RADIUS_M * lng * pi / 180.0
    poi_lat = EARTH_RADIUS_M * log(tan(pi / 4.0 + (lat_clamped * pi / 180.0) / 2.0))
    return poi_lng, poi_lat


def enrich_order_dict(order: dict[str, Any]) -> dict[str, Any]:
    """Add Mercator fields from real WGS84 input on an order dict."""
    out = dict(order)
    poi_lng, poi_lat = wgs84_to_web_mercator(
        float(order["lat_wgs84"]),
        float(order["lon_wgs84"]),
    )
    out["poi_lat"] = poi_lat
    out["poi_lng"] = poi_lng

    if "receipt_lat_wgs84" in order and "receipt_lon_wgs84" in order:
        receipt_lng, receipt_lat = wgs84_to_web_mercator(
            float(order["receipt_lat_wgs84"]),
            float(order["receipt_lon_wgs84"]),
        )
        out["receipt_lat"] = receipt_lat
        out["receipt_lng"] = receipt_lng
    elif "receipt_lat" not in out or "receipt_lng" not in out:
        out["receipt_lat"] = poi_lat
        out["receipt_lng"] = poi_lng

    return out
