"""DemandForecastPipeline wrapper."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from ml.adapters.demand_adapter import adapt_demand_payload
from ml.wrappers.base import BaseModelWrapper

MODEL_NAME = "lade_demand_forecaster"


def _normalize_demand_result(result: Any) -> dict[str, Any]:
    return {
        "granularity": result.granularity,
        "horizon": result.horizon,
        "dataset_kind": result.dataset_kind,
        "strategy": result.strategy,
        "panel_rows": result.panel_rows,
        "summary": (
            asdict(result.summary)
            if is_dataclass(result.summary)
            else vars(result.summary)
        ),
        "by_period": result.by_period,
        "by_city": result.by_city,
        "top_regions": result.top_regions,
    }


class DemandWrapper(BaseModelWrapper):
    prediction_type = "demand_forecast"
    model_name = MODEL_NAME

    def __init__(self, *, pipeline: Any | None = None) -> None:
        self._pipeline = pipeline

    def _get_pipeline(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline

        from ml_services.demand_forecasting.full_pipeline.config import (
            DAILY_MODEL_PATH,
            LADE_DIR,
            WEEKLY_STRATEGY_PATH,
        )
        from ml_services.demand_forecasting.full_pipeline.pipeline import (
            DemandForecastPipeline,
        )

        if not LADE_DIR.exists():
            raise FileNotFoundError(
                f"LaDe data not found at {LADE_DIR}. "
                "Place delivery CSVs under LaDe/delivery/."
            )
        if not DAILY_MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Daily model not found at {DAILY_MODEL_PATH}. "
                "Train the model or copy artifacts into ml_services/demand_forecasting/models/."
            )
        return DemandForecastPipeline(
            model_path=DAILY_MODEL_PATH,
            lade_dir=LADE_DIR,
            output_dir=None,
            strategy_path=WEEKLY_STRATEGY_PATH,
        )

    def run(self, context_payload: dict[str, Any]) -> dict[str, Any]:
        pipeline_kwargs = adapt_demand_payload(context_payload)
        pipeline = self._get_pipeline()
        raw = pipeline.run(**pipeline_kwargs, save_outputs=False)
        return {
            "prediction_type": self.prediction_type,
            "model_name": self.model_name,
            "result": _normalize_demand_result(raw),
        }
