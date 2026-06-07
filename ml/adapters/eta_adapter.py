"""Adapt Context Resolver ETA payloads to production inference schema."""

from __future__ import annotations

from typing import Any, TypedDict

from ml.validators import normalize_iso_datetime, validate_eta_payload


class ETAPipelinePayload(TypedDict):
    delivery_user_id: str
    from_dipan_id: str
    aoi_id: str
    receipt_time: str
    receipt_lat: float
    receipt_lng: float
    poi_lat: float
    poi_lng: float


def _normalize_id(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_receipt_time(value: Any) -> str:
    return normalize_iso_datetime(value, "receipt_time")


def adapt_eta_payload(context_payload: dict[str, Any]) -> ETAPipelinePayload:
    """
    Transform a Context Resolver eta_prediction payload into the exact dict
    expected by ml_services/eta-prediction/full_pipeline/inference.predict_eta.
    """
    validate_eta_payload(context_payload, schema="context")

    result: ETAPipelinePayload = {
        "delivery_user_id": _normalize_id(context_payload["delivery_user_id"]),
        "from_dipan_id": _normalize_id(context_payload["from_dipan_id"]),
        "aoi_id": _normalize_id(context_payload["aoi_id"]),
        "receipt_time": _normalize_receipt_time(context_payload["receipt_time"]),
        "receipt_lat": float(context_payload["receipt_lat"]),
        "receipt_lng": float(context_payload["receipt_lng"]),
        "poi_lat": float(context_payload["poi_lat"]),
        "poi_lng": float(context_payload["poi_lng"]),
    }

    validate_eta_payload(result, schema="pipeline")
    return result
