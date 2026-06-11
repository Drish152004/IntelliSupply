"""Full dispatch pipeline smoke test with synthetic data."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from config.paths import ROUTE_MODEL_PATH
from ml_services.route_prediction.full_pipeline.config import DATA_DIR
from ml_services.route_prediction.full_pipeline.pipeline import DeliveryPipeline


@pytest.mark.skipif(not ROUTE_MODEL_PATH.is_file(), reason="route model missing")
@pytest.mark.skipif(
    not (DATA_DIR / "synthetic_orders.json").is_file(),
    reason="synthetic_orders.json missing — run _generate_samples.py first",
)
def test_pipeline_run_small_batch():
    orders_path = DATA_DIR / "synthetic_orders.json"
    couriers_path = DATA_DIR / "synthetic_couriers.json"
    orders = json.loads(orders_path.read_text(encoding="utf-8"))
    couriers = json.loads(couriers_path.read_text(encoding="utf-8")) if couriers_path.is_file() else []

    pipeline = DeliveryPipeline(
        route_model_path=ROUTE_MODEL_PATH,
        couriers=couriers,
        output_dir=None,
    )
    result = pipeline.run(orders[:5], couriers=couriers, save_outputs=False)
    assert result.orders_processed == 5
    assert len(result.courier_assignments) == 5
    assert all(a.courier_id != "UNASSIGNED" for a in result.courier_assignments)
    for route in result.courier_routes:
        assert not hasattr(route, "cluster_id"), "cluster_id must be removed from CourierRoutePlan"
