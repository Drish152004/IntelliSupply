"""Assign incoming orders to pre-computed DBSCAN clusters."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

from ml_services.route_prediction.full_pipeline.config import EPS_RAD, ORDERS_CLUSTERED_PATH


@dataclass
class ClusterAssignment:
    order_id: str
    cluster_id: int
    city_name: str
    ds: int
    dist_to_centroid_km: float
    is_noise: bool


class ClusterAssigner:
    """Assign new orders to existing clusters via nearest member point (DBSCAN-style)."""

    def __init__(self, orders_clustered_path=ORDERS_CLUSTERED_PATH):
        self.orders = pd.read_csv(
            orders_clustered_path,
            usecols=["cluster_id", "city_name", "ds", "lat_wgs84", "lon_wgs84"],
        )
        self._member_trees: dict[tuple[str, int], BallTree] = {}
        self._member_meta: dict[tuple[str, int], pd.DataFrame] = {}
        self._build_member_trees()

    def _build_member_trees(self) -> None:
        clustered = self.orders[self.orders["cluster_id"] != -1]
        for (city, day), group in clustered.groupby(["city_name", "ds"]):
            coords = np.radians(group[["lat_wgs84", "lon_wgs84"]].values)
            self._member_trees[(city, day)] = BallTree(coords, metric="haversine")
            self._member_meta[(city, day)] = group.reset_index(drop=True)

    def assign_order(
        self,
        order_id: str,
        lat_wgs84: float,
        lon_wgs84: float,
        city_name: str,
        ds: int,
    ) -> ClusterAssignment:
        key = (city_name, ds)
        if key not in self._member_trees:
            return ClusterAssignment(
                order_id=order_id,
                cluster_id=-1,
                city_name=city_name,
                ds=ds,
                dist_to_centroid_km=float("nan"),
                is_noise=True,
            )

        query = np.radians([[lat_wgs84, lon_wgs84]])
        dist_rad, idx = self._member_trees[key].query(query, k=1)
        dist_km = float(dist_rad[0][0] * 6371.0)
        member = self._member_meta[key].iloc[int(idx[0][0])]

        if dist_km > EPS_RAD * 6371.0:
            return ClusterAssignment(
                order_id=order_id,
                cluster_id=-1,
                city_name=city_name,
                ds=ds,
                dist_to_centroid_km=dist_km,
                is_noise=True,
            )

        return ClusterAssignment(
            order_id=order_id,
            cluster_id=int(member["cluster_id"]),
            city_name=city_name,
            ds=ds,
            dist_to_centroid_km=dist_km,
            is_noise=False,
        )

    def assign_batch(self, orders: list[dict]) -> list[ClusterAssignment]:
        return [
            self.assign_order(
                order["order_id"],
                float(order["lat_wgs84"]),
                float(order["lon_wgs84"]),
                order["city_name"],
                int(order["ds"]),
            )
            for order in orders
        ]
