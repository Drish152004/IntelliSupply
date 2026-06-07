"""Adapt Context Resolver demand payloads to DemandForecastPipeline.run() kwargs."""

from __future__ import annotations

from typing import Any, TypedDict

from ml.validators import Granularity, DatasetKind, validate_demand_payload

DEFAULT_GRANULARITY: Granularity = "daily"
DEFAULT_DATASET_KIND: DatasetKind = "delivery"


class DemandPipelinePayload(TypedDict):
    granularity: Granularity
    horizon: int
    city: str
    dataset_kind: DatasetKind


def _normalize_horizon(value: Any) -> int:
    from ml.validators import _require_int

    return _require_int(value, "horizon")


def _normalize_granularity(value: Any | None) -> Granularity:
    if value is None or value == "":
        return DEFAULT_GRANULARITY
    text = str(value).strip().lower()
    if text not in ("daily", "weekly"):
        return DEFAULT_GRANULARITY
    return text  # type: ignore[return-value]


def _normalize_dataset_kind(value: Any | None) -> DatasetKind:
    if value is None or value == "":
        return DEFAULT_DATASET_KIND
    text = str(value).strip().lower()
    if text not in ("delivery", "pickup"):
        return DEFAULT_DATASET_KIND
    return text  # type: ignore[return-value]


def _resolve_city(context_payload: dict[str, Any]) -> str:
    city = context_payload.get("city") or context_payload.get("city_name")
    if city is None or str(city).strip() == "":
        from ml.validators import PayloadValidationError

        raise PayloadValidationError("city must be a non-empty string")
    return str(city).strip()


def adapt_demand_payload(context_payload: dict[str, Any]) -> DemandPipelinePayload:
    """
    Transform a Context Resolver demand_forecast payload into kwargs for
    DemandForecastPipeline.run().
    """
    city = _resolve_city(context_payload)
    working = {
        **context_payload,
        "city": city,
        "horizon": context_payload.get("horizon"),
        "granularity": _normalize_granularity(context_payload.get("granularity")),
        "dataset_kind": _normalize_dataset_kind(context_payload.get("dataset_kind")),
    }

    validate_demand_payload(
        {"city": city, "horizon": working["horizon"]},
        schema="context",
    )

    result: DemandPipelinePayload = {
        "granularity": working["granularity"],
        "horizon": _normalize_horizon(working["horizon"]),
        "city": city,
        "dataset_kind": working["dataset_kind"],
    }

    validate_demand_payload(result, schema="pipeline")
    return result
