"""Single source of truth for where each ML payload field is resolved from."""

from __future__ import annotations

FieldSource = str  # "graph" | "user" | "user_or_graph" | "system_default"

FIELD_SOURCES: dict[str, dict[str, FieldSource]] = {
    "eta_prediction": {
        "delivery_user_id": "graph",
        "from_dipan_id": "graph",
        "aoi_id": "graph",
        "receipt_lat": "graph",
        "receipt_lng": "graph",
        "poi_lat": "graph",
        "poi_lng": "graph",
        "receipt_time": "user_or_graph",
    },
    "route_prediction": {
        "order_id": "graph",
        "lat_wgs84": "graph",
        "lon_wgs84": "graph",
        "receipt_lat_wgs84": "graph",
        "receipt_lon_wgs84": "graph",
        "city_name": "graph",
        "ds": "graph",
        "typecode": "graph",
        "aoi_id": "graph",
        "delivery_day": "user_or_graph",
        "receipt_time": "user_or_graph",
    },
    "demand_forecast": {
        "city": "user",
        "horizon": "user",
        "granularity": "system_default",
        "dataset_kind": "system_default",
    },
}

SYSTEM_DEFAULTS: dict[str, dict[str, str | int]] = {
    "demand_forecast": {
        "granularity": "daily",
        "dataset_kind": "delivery",
        "horizon": 7,
    },
}


def field_sources_for_task(task: str) -> dict[str, FieldSource]:
    """Return field source mapping for a task."""
    return FIELD_SOURCES.get(task, {})
