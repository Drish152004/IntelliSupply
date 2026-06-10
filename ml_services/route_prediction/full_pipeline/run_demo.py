"""CLI entry point for the full delivery pipeline demo."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml_services.route_prediction.full_pipeline.config import (  # noqa: E402
    DATA_DIR,
    OUTPUT_DIR,
    ROUTE_MODEL_PATH,
)
from ml_services.route_prediction.full_pipeline.pipeline import DeliveryPipeline  # noqa: E402


def load_json(path: Path) -> list | dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    orders_path = DATA_DIR / "synthetic_orders.json"
    couriers_path = DATA_DIR / "synthetic_couriers.json"

    if not orders_path.is_file():
        raise FileNotFoundError(f"Missing {orders_path}")
    if not ROUTE_MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Route model not found at {ROUTE_MODEL_PATH}. "
            "Train the route ranker and export to models/route_ranker.pkl."
        )

    orders = load_json(orders_path)
    couriers = load_json(couriers_path) if couriers_path.is_file() else []

    print(f"Loading {len(orders)} synthetic orders …")
    print("Pipeline: cluster -> courier assign -> sequence predict")

    pipeline = DeliveryPipeline(
        route_model_path=ROUTE_MODEL_PATH,
        couriers=couriers,
        output_dir=OUTPUT_DIR,
    )
    result = pipeline.run(orders, couriers=couriers, save_outputs=True)

    print(f"\nProcessed {result.orders_processed} orders")
    print(f"Outputs written to: {result.output_dir}\n")

    for route in result.courier_routes:
        print(f"Courier {route.courier_id[:12]}…")
        print(f"  Cluster  : {route.cluster_id}")
        print(f"  City/day : {route.city_name} / {route.delivery_day}")
        print(f"  Stops    : {len(route.stops)}")
        print(f"  Sequence : {route.predicted_sequence}")
        print()


if __name__ == "__main__":
    main()
