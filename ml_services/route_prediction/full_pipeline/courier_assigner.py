"""Courier assignment — lookup pre-computed clusters or nearest available courier."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from ml_services.route_prediction.full_pipeline.cluster_assigner import ClusterAssignment
from ml_services.route_prediction.full_pipeline.config import (
    CLUSTER_ASSIGNMENTS_PATH,
    COURIER_TIE_BREAK_KM,
)


@dataclass
class CourierAssignment:
    order_id: str
    cluster_id: int
    courier_id: str
    city_name: str
    ds: int
    assignment_dist_km: float
    delivery_day: str


class CourierAssigner:
    """Resolve courier for each cluster using saved assignments or live matching."""

    def __init__(
        self,
        assignments_path=CLUSTER_ASSIGNMENTS_PATH,
        couriers: list[dict] | None = None,
    ):
        self.assignments = pd.read_csv(assignments_path)
        self.couriers = couriers or []
        self._courier_trees: dict[tuple[str, int], BallTree] = {}
        self._courier_meta: dict[tuple[str, int], pd.DataFrame] = {}
        if self.couriers:
            self._build_courier_trees()

    def _build_courier_trees(self) -> None:
        rows = []
        for c in self.couriers:
            rows.append(
                {
                    "courier_id": c["courier_id"],
                    "city_name": c["city_name"],
                    "ds": int(c["ds"]),
                    "start_lat_wgs84": c["start_lat_wgs84"],
                    "start_lon_wgs84": c["start_lon_wgs84"],
                    "workload": 0,
                }
            )
        cdf = pd.DataFrame(rows)
        for (city, day), group in cdf.groupby(["city_name", "ds"]):
            rad = np.radians(group[["start_lat_wgs84", "start_lon_wgs84"]].values)
            self._courier_trees[(city, day)] = BallTree(rad, metric="haversine")
            self._courier_meta[(city, day)] = group.reset_index(drop=True)

    def lookup_cluster_courier(
        self, cluster_id: int, city_name: str, ds: int
    ) -> tuple[str | None, float | None]:
        if cluster_id == -1:
            return None, None
        match = self.assignments[
            (self.assignments["cluster_id"] == cluster_id)
            & (self.assignments["city_name"] == city_name)
            & (self.assignments["ds"] == ds)
        ]
        if match.empty:
            return None, None
        row = match.iloc[0]
        return str(row["assigned_courier"]), float(row["assignment_dist_km"])

    def nearest_courier(
        self,
        lat_wgs84: float,
        lon_wgs84: float,
        city_name: str,
        ds: int,
    ) -> tuple[str | None, float]:
        key = (city_name, ds)
        if key not in self._courier_trees:
            return None, float("nan")

        query = np.radians([[lat_wgs84, lon_wgs84]])
        tree = self._courier_trees[key]
        meta = self._courier_meta[key]
        k = min(3, len(meta))
        dist_rad, indices = tree.query(query, k=k)
        best_idx = int(indices[0][0])
        best_dist_km = float(dist_rad[0][0] * 6371.0)

        tie_candidates = []
        for rank in range(k):
            idx = int(indices[0][rank])
            dist_km = float(dist_rad[0][rank] * 6371.0)
            if dist_km - best_dist_km <= COURIER_TIE_BREAK_KM:
                tie_candidates.append(idx)

        if len(tie_candidates) > 1:
            workloads = meta.iloc[tie_candidates]["workload"]
            best_idx = int(meta.iloc[tie_candidates].iloc[workloads.argmin()].name)

        courier_id = str(meta.iloc[best_idx]["courier_id"])
        meta.loc[best_idx, "workload"] += 1
        self._courier_meta[key] = meta
        return courier_id, best_dist_km

    def assign_order(
        self,
        cluster: ClusterAssignment,
        lat_wgs84: float,
        lon_wgs84: float,
        delivery_day: str,
    ) -> CourierAssignment:
        courier_id, dist_km = self.lookup_cluster_courier(
            cluster.cluster_id, cluster.city_name, cluster.ds
        )

        if courier_id is None:
            courier_id, dist_km = self.nearest_courier(
                lat_wgs84, lon_wgs84, cluster.city_name, cluster.ds
            )

        if courier_id is None:
            courier_id = "UNASSIGNED"
            dist_km = float("nan")

        return CourierAssignment(
            order_id=cluster.order_id,
            cluster_id=cluster.cluster_id,
            courier_id=courier_id,
            city_name=cluster.city_name,
            ds=cluster.ds,
            assignment_dist_km=dist_km if dist_km is not None else float("nan"),
            delivery_day=delivery_day,
        )

    def assign_batch(
        self,
        clusters: list[ClusterAssignment],
        orders_by_id: dict[str, dict],
    ) -> list[CourierAssignment]:
        results = []
        for cluster in clusters:
            order = orders_by_id[cluster.order_id]
            results.append(
                self.assign_order(
                    cluster,
                    float(order["lat_wgs84"]),
                    float(order["lon_wgs84"]),
                    order.get("delivery_day", str(cluster.ds)),
                )
            )
        return results

    def group_by_courier(
        self, assignments: list[CourierAssignment]
    ) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for a in assignments:
            grouped.setdefault(a.courier_id, []).append(a.order_id)
        return grouped

    def group_by_courier_cluster(
        self, assignments: list[CourierAssignment]
    ) -> dict[tuple[str, int, str, int], list[str]]:
        """One route per courier + cluster + city + day (avoids cross-region mega-routes)."""
        grouped: dict[tuple[str, int, str, int], list[str]] = {}
        for a in assignments:
            key = (a.courier_id, a.cluster_id, a.city_name, a.ds)
            grouped.setdefault(key, []).append(a.order_id)
        return grouped
