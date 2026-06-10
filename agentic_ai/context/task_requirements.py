"""Required ML payload fields per orchestrator task."""

from __future__ import annotations

ML_TASKS: frozenset[str] = frozenset({
    "eta_prediction",
    "route_prediction",
    "demand_forecast",
})

TASK_REQUIRED_FIELDS: dict[str, frozenset[str]] = {
    "eta_prediction": frozenset({
        "delivery_user_id",
        "from_dipan_id",
        "aoi_id",
        "receipt_time",
        "receipt_lat",
        "receipt_lng",
        "poi_lat",
        "poi_lng",
    }),
    "route_prediction": frozenset({
        "order_id",
        "lat_wgs84",
        "lon_wgs84",
        "receipt_lat_wgs84",
        "receipt_lon_wgs84",
        "city_name",
        "ds",
        "delivery_day",
        "receipt_time",
        "typecode",
        "aoi_id",
    }),
    "demand_forecast": frozenset({
        "records",
    }),
}

# Minimum entities required before graph search / enrichment can run.
QUERY_ENTITY_REQUIREMENTS: dict[str, tuple[tuple[str, ...], ...]] = {
    "eta_prediction": (("order_id",), ("shipment_id",)),
    "route_prediction": (("order_id",), ("from_hub", "to_hub")),
    "demand_forecast": (("city",), ("city_name",)),
}


def is_ml_task(task: str) -> bool:
    """Return True when the task requires ML payload preparation."""
    return task in ML_TASKS


def required_fields_for_task(task: str) -> frozenset[str]:
    """Return required payload fields for a task."""
    return TASK_REQUIRED_FIELDS.get(task, frozenset())
