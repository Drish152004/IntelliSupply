"""Demand forecasting inference helpers."""

from __future__ import annotations

from typing import Any

from services.registry import _ensure_demand_path, get_demand_bundle


def predict_demand(records: list[dict[str, Any]]) -> dict[str, Any]:
    _ensure_demand_path()
    from inference import predict

    bundle = get_demand_bundle()
    return {"predictions": predict(records, bundle=bundle)}
