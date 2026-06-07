"""Demand forecasting inference via Hugging Face Space (same path as agent ml_bridge)."""

from __future__ import annotations

from typing import Any

from services.registry import _ensure_demand_path


def _import_hf_client():
    _ensure_demand_path()
    import hf_client

    return hf_client


def check_health() -> dict[str, Any]:
    return _import_hf_client().health()


def get_meta() -> dict[str, Any]:
    return _import_hf_client().meta()


def predict_demand(records: list[dict[str, Any]]) -> dict[str, Any]:
    predictions = _import_hf_client().predict_demand(records)
    return {"predictions": predictions}
