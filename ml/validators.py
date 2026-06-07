"""Centralized payload validation for ML pipeline adapters."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

Granularity = Literal["daily", "weekly"]
DatasetKind = Literal["delivery", "pickup"]

ETA_PIPELINE_FIELDS: frozenset[str] = frozenset({
    "delivery_user_id",
    "from_dipan_id",
    "aoi_id",
    "receipt_time",
    "receipt_lat",
    "receipt_lng",
    "poi_lat",
    "poi_lng",
})

ETA_CONTEXT_FIELDS: frozenset[str] = ETA_PIPELINE_FIELDS

ROUTE_ORDER_FIELDS: frozenset[str] = frozenset({
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
})

ROUTE_CONTEXT_FIELDS: frozenset[str] = ROUTE_ORDER_FIELDS

DEMAND_PIPELINE_FIELDS: frozenset[str] = frozenset({
    "granularity",
    "horizon",
    "city",
    "dataset_kind",
})

DEMAND_CONTEXT_FIELDS: frozenset[str] = frozenset({
    "city",
    "horizon",
})

VALID_GRANULARITIES: frozenset[str] = frozenset({"daily", "weekly"})
VALID_DATASET_KINDS: frozenset[str] = frozenset({"delivery", "pickup"})

DAILY_HORIZON_MAX = 28
WEEKLY_HORIZON_MAX = 12


class PayloadValidationError(ValueError):
    """Raised when a payload fails schema or type validation."""


def _missing_fields(payload: dict[str, Any], required: frozenset[str]) -> list[str]:
    return sorted(
        field
        for field in required
        if field not in payload or payload[field] is None or payload[field] == ""
    )


def _require_non_empty_str(value: Any, field: str) -> str:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise PayloadValidationError(f"{field} must be a non-empty string")
    text = str(value).strip()
    if not text:
        raise PayloadValidationError(f"{field} must be a non-empty string")
    return text


def _require_float(value: Any, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise PayloadValidationError(f"{field} must be a float") from exc


def _require_int(value: Any, field: str) -> int:
    try:
        if isinstance(value, bool):
            raise ValueError("bool is not a valid integer")
        return int(value)
    except (TypeError, ValueError) as exc:
        raise PayloadValidationError(f"{field} must be an integer") from exc


def normalize_iso_datetime(value: Any, field: str) -> str:
    text = _require_non_empty_str(value, field)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PayloadValidationError(
            f"{field} must be an ISO-8601 datetime string"
        ) from exc
    return parsed.isoformat(sep="T")


def _require_iso_datetime(value: Any, field: str) -> str:
    return normalize_iso_datetime(value, field)


def _require_id(value: Any, field: str) -> str:
    return _require_non_empty_str(value, field)


def validate_eta_payload(
    payload: dict[str, Any],
    *,
    schema: Literal["context", "pipeline"] = "pipeline",
) -> None:
    """
    Validate an ETA context or pipeline-ready payload.

    Pipeline schema matches ml_services/eta-prediction production inference input.
    """
    required = ETA_CONTEXT_FIELDS if schema == "context" else ETA_PIPELINE_FIELDS
    missing = _missing_fields(payload, required)
    if missing:
        raise PayloadValidationError(f"Missing required ETA fields: {', '.join(missing)}")

    _require_id(payload["delivery_user_id"], "delivery_user_id")
    _require_id(payload["from_dipan_id"], "from_dipan_id")
    _require_id(payload["aoi_id"], "aoi_id")
    _require_iso_datetime(payload["receipt_time"], "receipt_time")
    _require_float(payload["receipt_lat"], "receipt_lat")
    _require_float(payload["receipt_lng"], "receipt_lng")
    _require_float(payload["poi_lat"], "poi_lat")
    _require_float(payload["poi_lng"], "poi_lng")


def validate_route_payload(
    payload: dict[str, Any],
    *,
    schema: Literal["context", "pipeline"] = "pipeline",
) -> None:
    """
    Validate a route context payload or a single DeliveryPipeline order dict.

    Pipeline schema matches ml_services/route_prediction/full_pipeline/pipeline.py
    order inputs (WGS84 coordinates; enrichment happens inside the pipeline).
    """
    required = ROUTE_CONTEXT_FIELDS if schema == "context" else ROUTE_ORDER_FIELDS
    missing = _missing_fields(payload, required)
    if missing:
        raise PayloadValidationError(f"Missing required route fields: {', '.join(missing)}")

    _require_non_empty_str(payload["order_id"], "order_id")
    _require_float(payload["lat_wgs84"], "lat_wgs84")
    _require_float(payload["lon_wgs84"], "lon_wgs84")
    _require_float(payload["receipt_lat_wgs84"], "receipt_lat_wgs84")
    _require_float(payload["receipt_lon_wgs84"], "receipt_lon_wgs84")
    _require_non_empty_str(payload["city_name"], "city_name")
    _require_int(payload["ds"], "ds")
    _require_non_empty_str(payload["delivery_day"], "delivery_day")
    _require_iso_datetime(payload["receipt_time"], "receipt_time")
    _require_non_empty_str(payload["typecode"], "typecode")
    _require_id(payload["aoi_id"], "aoi_id")


def validate_demand_payload(
    payload: dict[str, Any],
    *,
    schema: Literal["context", "pipeline"] = "pipeline",
) -> None:
    """
    Validate a demand context or DemandForecastPipeline.run() kwargs payload.
    """
    required = DEMAND_CONTEXT_FIELDS if schema == "context" else DEMAND_PIPELINE_FIELDS
    missing = _missing_fields(payload, required)
    if missing:
        raise PayloadValidationError(f"Missing required demand fields: {', '.join(missing)}")

    city = _require_non_empty_str(payload["city"], "city")
    if not city:
        raise PayloadValidationError("city must be a non-empty string")

    horizon = _require_int(payload["horizon"], "horizon")
    if horizon < 1:
        raise PayloadValidationError("horizon must be at least 1")

    if schema == "context":
        return

    granularity = str(payload["granularity"]).strip().lower()
    if granularity not in VALID_GRANULARITIES:
        raise PayloadValidationError(
            f"granularity must be one of: {', '.join(sorted(VALID_GRANULARITIES))}"
        )

    dataset_kind = str(payload["dataset_kind"]).strip().lower()
    if dataset_kind not in VALID_DATASET_KINDS:
        raise PayloadValidationError(
            f"dataset_kind must be one of: {', '.join(sorted(VALID_DATASET_KINDS))}"
        )

    max_horizon = DAILY_HORIZON_MAX if granularity == "daily" else WEEKLY_HORIZON_MAX
    if horizon > max_horizon:
        raise PayloadValidationError(
            f"horizon max is {max_horizon} for {granularity} granularity"
        )
