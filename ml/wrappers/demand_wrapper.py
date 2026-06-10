"""Demand forecasting wrapper — calls hosted Hugging Face Space."""

from __future__ import annotations

from typing import Any

from ml.adapters.demand_adapter import adapt_demand_payload
from ml.wrappers.base import BaseModelWrapper
from models import hf_client

MODEL_NAME = "lade_demand_forecaster"


class DemandWrapper(BaseModelWrapper):
    prediction_type = "demand_forecast"
    model_name = MODEL_NAME

    def __init__(self, *, client: Any | None = None) -> None:
        self._client = client or hf_client

    def run(self, context_payload: dict[str, Any]) -> dict[str, Any]:
        records = adapt_demand_payload(context_payload)
        predictions = self._client.predict_demand(records)
        return {
            "prediction_type": self.prediction_type,
            "model_name": self.model_name,
            "result": {"predictions": predictions},
        }
