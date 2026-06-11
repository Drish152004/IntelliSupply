"""Route DeliveryPipeline wrapper."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ml.adapters.route_adapter import adapt_route_payload
from ml.wrappers.base import BaseModelWrapper

MODEL_NAME = "route_ranker"


def _normalize_route_result(result: Any) -> dict[str, Any]:
    return {
        "orders_processed": result.orders_processed,
        "courier_routes": [
            {
                "courier_id": route.courier_id,
                "city_name": route.city_name,
                "delivery_day": route.delivery_day,
                "order_ids": route.order_ids,
                "predicted_sequence": route.predicted_sequence,
                "stops": route.stops,
            }
            for route in result.courier_routes
        ],
        "courier_assignments": [asdict(item) for item in result.courier_assignments],
    }


class RouteWrapper(BaseModelWrapper):
    prediction_type = "route"
    model_name = MODEL_NAME

    def __init__(self, *, pipeline: Any | None = None) -> None:
        self._pipeline = pipeline

    def _get_pipeline(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline

        from ml_services.route_prediction.full_pipeline.config import ROUTE_MODEL_PATH
        from ml_services.route_prediction.full_pipeline.pipeline import DeliveryPipeline

        if not ROUTE_MODEL_PATH.is_file():
            raise FileNotFoundError(
                f"Route model not found at {ROUTE_MODEL_PATH}. "
                "Train the route ranker and export to models/route_ranker.pkl."
            )
        return DeliveryPipeline(route_model_path=ROUTE_MODEL_PATH, output_dir=None)

    def run(self, context_payload: dict[str, Any]) -> dict[str, Any]:
        orders = adapt_route_payload(context_payload)
        pipeline = self._get_pipeline()
        raw = pipeline.run(orders, save_outputs=False)
        return {
            "prediction_type": self.prediction_type,
            "model_name": self.model_name,
            "result": _normalize_route_result(raw),
        }
