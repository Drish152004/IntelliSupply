"""End-to-end delivery pipeline: hub WGS84 → courier assignment → sequence prediction."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from ml_services.route_prediction.full_pipeline.coordinates import enrich_order_dict
from ml_services.route_prediction.full_pipeline.courier_assigner import (
    CourierAssigner,
    CourierAssignment,
)
from ml_services.route_prediction.route_predictor import RoutePredictor


@dataclass
class CourierRoutePlan:
    courier_id: str
    city_name: str
    delivery_day: str
    order_ids: list[str]
    predicted_sequence: list[str]
    stops: list[dict[str, Any]]


@dataclass
class PipelineResult:
    orders_processed: int
    courier_assignments: list[CourierAssignment]
    courier_routes: list[CourierRoutePlan] = field(default_factory=list)
    output_dir: str = ""


class DeliveryPipeline:
    """Hub-based order → courier assignment → predicted delivery sequence."""

    def __init__(
        self,
        *,
        route_model_path: Path,
        couriers: list[dict] | None = None,
        output_dir: Path | None = None,
    ):
        self.courier_assigner = CourierAssigner()
        self.predictor = RoutePredictor.load(route_model_path)
        self._default_couriers = couriers or []
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
        effective_couriers = couriers if couriers is not None else self._default_couriers
        prepared = self._prepare_orders(orders)
        orders_by_id = {o["order_id"]: o for o in prepared}

        courier_results = self.courier_assigner.assign_batch(prepared, effective_couriers)
        grouped = self.courier_assigner.group_by_courier_day(courier_results)

        courier_routes: list[CourierRoutePlan] = []
        for (courier_id, city_name, delivery_day), order_ids in grouped.items():
            courier_orders = [orders_by_id[oid] for oid in order_ids]
            route_df = self._orders_for_predictor(courier_orders)
            sequence = self.predictor.predict_full_sequence(route_df)
            stops = self._build_stops(sequence, orders_by_id)

            courier_routes.append(
                CourierRoutePlan(
                    courier_id=courier_id,
                    city_name=city_name,
                    delivery_day=delivery_day,
                    order_ids=order_ids,
                    predicted_sequence=sequence,
                    stops=stops,
                )
            )

        if save_outputs and self.output_dir:
            self._save_outputs(prepared, courier_results, courier_routes)

        return PipelineResult(
            orders_processed=len(prepared),
            courier_assignments=courier_results,
            courier_routes=courier_routes,
            output_dir=str(self.output_dir) if self.output_dir else "",
        )

    def _save_outputs(
        self,
        orders: list[dict],
        courier_assignments: list[CourierAssignment],
        routes: list[CourierRoutePlan],
    ) -> None:
        assert self.output_dir is not None
        self.output_dir.mkdir(parents=True, exist_ok=True)

        assignment_df = pd.DataFrame([asdict(a) for a in courier_assignments])
        orders_df = pd.DataFrame(orders)

        merged = orders_df.merge(
            assignment_df[["order_id", "courier_id", "delivery_day", "assignment_dist_m", "from_hub_name"]],
            on="order_id",
            how="left",
        )
        merged.to_csv(self.output_dir / "orders_with_assignments.csv", index=False)

        route_payload = [
            {
                "route_prediction_id": f"{plan.courier_id}_{plan.delivery_day}",
                "courier_id": plan.courier_id,
                "city_name": plan.city_name,
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
