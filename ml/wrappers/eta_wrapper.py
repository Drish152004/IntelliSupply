"""ETA production pipeline wrapper."""

from __future__ import annotations

import sys
from typing import Any

from config.paths import ETA_PREDICTION_ROOT
from ml.adapters.eta_adapter import adapt_eta_payload
from ml.wrappers.base import BaseModelWrapper

MODEL_NAME = "lgbm_eta_model"


def _ensure_eta_path() -> None:
    path = str(ETA_PREDICTION_ROOT)
    if path not in sys.path:
        sys.path.insert(0, path)


class ETAWrapper(BaseModelWrapper):
    prediction_type = "eta"
    model_name = MODEL_NAME

    def run(self, context_payload: dict[str, Any]) -> dict[str, Any]:
        pipeline_input = adapt_eta_payload(context_payload)
        _ensure_eta_path()
        from full_pipeline.inference import predict_eta

        raw = predict_eta(pipeline_input)
        return {
            "prediction_type": self.prediction_type,
            "model_name": self.model_name,
            "result": {
                "eta_minutes": raw["eta_minutes"],
            },
        }
