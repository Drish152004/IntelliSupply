"""Demand forecasting inference via Hugging Face Space (same path as agent ml_bridge)."""

from __future__ import annotations

from typing import Any

from models import hf_client


def check_health() -> dict[str, Any]:
    return hf_client.health()


def get_meta() -> dict[str, Any]:
    return hf_client.meta()


def predict_demand(records: list[dict[str, Any]]) -> dict[str, Any]:
    predictions = hf_client.predict_demand(records)
    return {"predictions": predictions}
