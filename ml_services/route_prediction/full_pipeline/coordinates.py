"""Convert real-world China WGS84 ↔ model / Mercator coordinates."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ml_services.coordinate_mapping import (
    WGS84Point,
    build_default_mvp_mapper,
    wgs84_to_web_mercator,
)

_mapper = build_default_mvp_mapper()


@dataclass(frozen=True)
class OrderCoordinates:
    """All coordinate representations for one order stop."""

    lat_wgs84: float
    lon_wgs84: float
    poi_lat: float  # Web Mercator northing (Delivery.csv convention)
    poi_lng: float  # Web Mercator easting
    model_lat: float
    model_lng: float


def real_wgs84_to_order_coords(lat: float, lon: float) -> OrderCoordinates:
    """Map real China GPS to Mercator (route model) and model-space coords."""
    real = WGS84Point(lat=lat, lng=lon)
    synthetic = _mapper.to_synthetic(real)
    metric = wgs84_to_web_mercator(real)
    return OrderCoordinates(
        lat_wgs84=lat,
        lon_wgs84=lon,
        poi_lng=metric.x,
        poi_lat=metric.y,
        model_lat=synthetic.lat,
        model_lng=synthetic.lng,
    )


def enrich_order_dict(order: dict[str, Any]) -> dict[str, Any]:
    """Add Mercator + model-space fields from real WGS84 input on an order dict."""
    out = dict(order)
    dest = real_wgs84_to_order_coords(float(order["lat_wgs84"]), float(order["lon_wgs84"]))
    out["poi_lat"] = dest.poi_lat
    out["poi_lng"] = dest.poi_lng
    out["model_lat"] = dest.model_lat
    out["model_lng"] = dest.model_lng

    if "receipt_lat_wgs84" in order and "receipt_lon_wgs84" in order:
        receipt = real_wgs84_to_order_coords(
            float(order["receipt_lat_wgs84"]),
            float(order["receipt_lon_wgs84"]),
        )
        out["receipt_lat"] = receipt.poi_lat
        out["receipt_lng"] = receipt.poi_lng
    elif "receipt_lat" not in out or "receipt_lng" not in out:
        # Default: courier starts at first stop's pickup ≈ destination for demo
        out["receipt_lat"] = dest.poi_lat
        out["receipt_lng"] = dest.poi_lng

    return out


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import numpy as np

    lat1_r, lon1_r = np.radians([lat1, lon1])
    lat2_r, lon2_r = np.radians([lat2, lon2])
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlon / 2) ** 2
    return float(2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a)))


EARTH_RADIUS_KM = 6371.0
