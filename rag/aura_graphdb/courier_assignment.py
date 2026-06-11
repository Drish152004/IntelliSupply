"""Courier assignment logic: nearby-hub consolidation + nearest-courier fallback.

This module is the single source of truth for courier selection. It is used by:
  - aura_order.py  (live FastAPI shipment create)
  - ml_services/route_prediction/full_pipeline/courier_assigner.py  (offline batch demo)

Assignment tiers (in priority order):
  1. Consolidation: a courier already has a stop within NEARBY_HUB_KM of the new pickup
     on the same delivery_day → assign to the closest such courier.
  2. Fallback: nearest active courier in the city to the pickup location.
"""

from __future__ import annotations

from typing import Any

from aura_graphdb.hub_coordinates import NEARBY_HUB_KM, haversine_distance_m

_KM_TO_M = 1000.0


def select_courier_for_order(
    pickup_lat: float,
    pickup_lon: float,
    delivery_day: str,
    couriers: list[dict[str, Any]],
    existing_orders: list[dict[str, Any]],
) -> tuple[dict[str, Any], float]:
    """Select the best courier for a new order pickup.

    Args:
        pickup_lat: WGS84 latitude of the pickup hub.
        pickup_lon: WGS84 longitude of the pickup hub.
        delivery_day: ISO date string (YYYY-MM-DD).
        couriers: list of active courier dicts, each with:
            courier_id, start_lat_wgs84, start_lon_wgs84, city_name
        existing_orders: list of already-assigned orders on the same (city, delivery_day),
            each with: assigned_courier_id, receipt_lat_wgs84, receipt_lon_wgs84,
            lat_wgs84, lon_wgs84

    Returns:
        (chosen_courier_dict, distance_m_from_pickup)
    """
    nearby_km = NEARBY_HUB_KM

    couriers_by_id = {c["courier_id"]: c for c in couriers}

    # Tier 1: consolidation — find couriers with a same-day stop within NEARBY_HUB_KM
    courier_min_dist: dict[str, float] = {}
    for order in existing_orders:
        if order.get("delivery_day") != delivery_day:
            continue
        cid = order.get("assigned_courier_id")
        if not cid or cid not in couriers_by_id:
            continue

        # Check both pickup (receipt) and delivery stops
        for lat_key, lon_key in [
            ("receipt_lat_wgs84", "receipt_lon_wgs84"),
            ("lat_wgs84", "lon_wgs84"),
        ]:
            stop_lat = order.get(lat_key)
            stop_lon = order.get(lon_key)
            if stop_lat is None or stop_lon is None:
                continue
            dist_m = haversine_distance_m(pickup_lat, pickup_lon, float(stop_lat), float(stop_lon))
            if dist_m <= nearby_km * _KM_TO_M:
                prev = courier_min_dist.get(cid, float("inf"))
                courier_min_dist[cid] = min(prev, dist_m)

    if courier_min_dist:
        best_id = min(courier_min_dist, key=lambda cid: courier_min_dist[cid])
        chosen = couriers_by_id[best_id]
        dist_m = haversine_distance_m(
            pickup_lat,
            pickup_lon,
            float(chosen["start_lat_wgs84"]),
            float(chosen["start_lon_wgs84"]),
        )
        return chosen, dist_m

    # Tier 2: nearest active courier to pickup
    def _dist_to_pickup(courier: dict[str, Any]) -> float:
        return haversine_distance_m(
            pickup_lat,
            pickup_lon,
            float(courier["start_lat_wgs84"]),
            float(courier["start_lon_wgs84"]),
        )

    best = min(couriers, key=_dist_to_pickup)
    return best, _dist_to_pickup(best)
