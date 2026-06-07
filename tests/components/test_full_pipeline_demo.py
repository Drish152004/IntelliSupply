"""Full dispatch pipeline smoke test with synthetic data."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from config.paths import CLUSTER_ASSIGNMENTS_PATH, ROUTE_MODEL_PATH
from ml_services.route_prediction.full_pipeline.config import DATA_DIR
from ml_services.route_prediction.full_pipeline.pipeline import DeliveryPipeline


@pytest.mark.skipif(not ROUTE_MODEL_PATH.is_file(), reason="route model missing")
@pytest.mark.skipif(not CLUSTER_ASSIGNMENTS_PATH.is_file(), reason="cluster assignments missing")
def test_pipeline_run_small_batch():
    orders_path = DATA_DIR / "synthetic_orders.json"
    couriers_path = DATA_DIR / "synthetic_couriers.json"
    orders = json.loads(orders_path.read_text(encoding="utf-8"))
    couriers = json.loads(couriers_path.read_text(encoding="utf-8"))

    pipeline = DeliveryPipeline(
        route_model_path=ROUTE_MODEL_PATH,
        couriers=couriers,
        output_dir=None,
    )
    result = pipeline.run(orders[:5], couriers=couriers, save_outputs=False)
    assert result.orders_processed == 5
