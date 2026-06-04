"""End-to-end delivery pipeline: cluster → courier → sequence prediction."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ml_services.route_prediction.full_pipeline.cluster_assigner import (
    ClusterAssigner,
    ClusterAssignment,
)
from ml_services.route_prediction.full_pipeline.coordinates import enrich_order_dict
from ml_services.route_prediction.full_pipeline.courier_assigner import (
    CourierAssigner,
    CourierAssignment,
)
from ml_services.route_prediction.route_predictor import RoutePredictor


@dataclass
class CourierRoutePlan:
    courier_id: str
    cluster_id: int
    city_name: str
    ds: int
    delivery_day: str
    order_ids: list[str]
    predicted_sequence: list[str]
    stops: list[dict[str, Any]]


@dataclass
class PipelineResult:
    orders_processed: int
    cluster_assignments: list[ClusterAssignment]
    courier_assignments: list[CourierAssignment]
    courier_routes: list[CourierRoutePlan] = field(default_factory=list)
    output_dir: str = ""


class DeliveryPipeline:
    """Real-world order → cluster → courier → predicted delivery sequence."""

    def __init__(
        self,
        *,
        route_model_path: Path,
        couriers: list[dict] | None = None,
        output_dir: Path | None = None,
    ):
        self.cluster_assigner = ClusterAssigner()
        self.courier_assigner = CourierAssigner(couriers=couriers)
        self.predictor = RoutePredictor.load(route_model_path)
        self.output_dir = output_dir

    def _prepare_orders(self, orders: list[dict]) -> list[dict]:
        return [enrich_order_dict(order) for order in orders]

    def _orders_for_predictor(self, orders: list[dict]) -> pd.DataFrame:
        rows = []
        for o in orders:
            rows.append(
                {
                    "order_id": o["order_id"],
                    "poi_lat": o["poi_lat"],
                    "poi_lng": o["poi_lng"],
                    "receipt_time": o["receipt_time"],
                    "receipt_lat": o["receipt_lat"],
                    "receipt_lng": o["receipt_lng"],
                    "city_name": o["city_name"],
                    "typecode": o["typecode"],
                    "aoi_id": o["aoi_id"],
                }
            )
        return pd.DataFrame(rows)

    def _build_stops(
        self, sequence: list[str], orders_by_id: dict[str, dict]
    ) -> list[dict[str, Any]]:
        stops = []
        for seq, oid in enumerate(sequence, start=1):
            o = orders_by_id[oid]
            stops.append(
                {
                    "sequence": seq,
                    "order_id": oid,
                    "lat_wgs84": o["lat_wgs84"],
                    "lon_wgs84": o["lon_wgs84"],
                }
            )
        return stops

    def run(
        self,
        orders: list[dict],
        *,
        couriers: list[dict] | None = None,
        save_outputs: bool = True,
    ) -> PipelineResult:
        prepared = self._prepare_orders(orders)
        orders_by_id = {o["order_id"]: o for o in prepared}

        cluster_results = self.cluster_assigner.assign_batch(prepared)
        courier_results = self.courier_assigner.assign_batch(cluster_results, orders_by_id)
        grouped = self.courier_assigner.group_by_courier_cluster(courier_results)

        courier_routes: list[CourierRoutePlan] = []
        for (courier_id, cluster_id, city_name, ds), order_ids in grouped.items():
            courier_orders = [orders_by_id[oid] for oid in order_ids]
            route_df = self._orders_for_predictor(courier_orders)
            sequence = self.predictor.predict_full_sequence(route_df)
            stops = self._build_stops(sequence, orders_by_id)

            meta = next(
                ca
                for ca in courier_results
                if ca.courier_id == courier_id and ca.order_id == order_ids[0]
            )

            courier_routes.append(
                CourierRoutePlan(
                    courier_id=courier_id,
                    cluster_id=cluster_id,
                    city_name=city_name,
                    ds=ds,
                    delivery_day=meta.delivery_day,
                    order_ids=order_ids,
                    predicted_sequence=sequence,
                    stops=stops,
                )
            )

        if save_outputs and self.output_dir:
            self._save_outputs(
                prepared, cluster_results, courier_results, courier_routes
            )

        return PipelineResult(
            orders_processed=len(prepared),
            cluster_assignments=cluster_results,
            courier_assignments=courier_results,
            courier_routes=courier_routes,
            output_dir=str(self.output_dir) if self.output_dir else "",
        )

    def _save_outputs(
        self,
        orders: list[dict],
        clusters: list[ClusterAssignment],
        couriers_out: list[CourierAssignment],
        routes: list[CourierRoutePlan],
    ) -> None:
        assert self.output_dir is not None
        self.output_dir.mkdir(parents=True, exist_ok=True)

        cluster_df = pd.DataFrame([asdict(c) for c in clusters])
        courier_df = pd.DataFrame([asdict(c) for c in couriers_out])
        orders_df = pd.DataFrame(orders)

        merged = orders_df.merge(cluster_df, on="order_id", how="left", suffixes=("", "_cluster"))
        merged = merged.merge(
            courier_df[["order_id", "courier_id", "delivery_day", "assignment_dist_km"]],
            on="order_id",
            how="left",
        )
        merged.to_csv(self.output_dir / "orders_with_assignments.csv", index=False)

        route_payload = [
            {
                "courier_id": plan.courier_id,
                "cluster_id": plan.cluster_id,
                "city_name": plan.city_name,
                "ds": plan.ds,
                "delivery_day": plan.delivery_day,
                "order_ids": plan.order_ids,
                "predicted_sequence": plan.predicted_sequence,
                "stops": plan.stops,
            }
            for plan in routes
        ]

        with open(self.output_dir / "assigned_routes.json", "w", encoding="utf-8") as f:
            json.dump(route_payload, f, indent=2, ensure_ascii=False)

        summary = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "orders_processed": len(orders),
            "courier_routes": len(routes),
            "routes": [
                {
                    "courier_id": p.courier_id,
                    "cluster_id": p.cluster_id,
                    "city_name": p.city_name,
                    "delivery_day": p.delivery_day,
                    "stops": len(p.stops),
                    "predicted_sequence": p.predicted_sequence,
                }
                for p in routes
            ],
        }
        with open(self.output_dir / "pipeline_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
