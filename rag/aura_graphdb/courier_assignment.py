"""Courier assignment logic: nearby-hub consolidation + hub-scoped fallback.

This module is the single source of truth for courier selection. It is used by:
  - aura_order.py  (live FastAPI shipment create)
  - ml_services/route_prediction/full_pipeline/courier_assigner.py  (offline batch demo)

Assignment tiers (in priority order):
  1. Consolidation: a courier already has a stop within NEARBY_HUB_KM of the new pickup
     on the same delivery_day AND has fewer than MAX_ORDERS_PER_DAY orders → assign to
     the closest such courier.
  2. Hub fallback: any active courier assigned to the pickup hub with fewer than
     MAX_ORDERS_PER_DAY orders on that delivery_day → assign to the nearest among them.
"""

from __future__ import annotations

import math
from typing import Any

NEARBY_HUB_KM = 5.0
_KM_TO_M = 1000.0
MAX_ORDERS_PER_DAY = 20
_EARTH_RADIUS_M = 6_371_000.0


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in metres between two WGS84 points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * _EARTH_RADIUS_M * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _count_orders_per_courier(existing_orders: list[dict[str, Any]], delivery_day: str) -> dict[str, int]:
    """Count how many orders each courier already has on delivery_day."""
    counts: dict[str, int] = {}
    for order in existing_orders:
        if order.get("delivery_day") != delivery_day:
            continue
        cid = order.get("assigned_courier_id")
        if cid:
            counts[cid] = counts.get(cid, 0) + 1
    return counts


def select_courier_for_order(
    pickup_lat: float,
    pickup_lon: float,
    delivery_day: str,
    couriers: list[dict[str, Any]],
    existing_orders: list[dict[str, Any]],
    pickup_hub_name: str | None = None,
) -> tuple[dict[str, Any], float]:
    """Select the best courier for a new order pickup.

    Args:
        pickup_lat: WGS84 latitude of the pickup hub.
        pickup_lon: WGS84 longitude of the pickup hub.
        delivery_day: ISO date string (YYYY-MM-DD).
        couriers: list of active courier dicts, each with:
            courier_id, start_lat_wgs84, start_lon_wgs84, city_name,
            and optionally hub_name for tier-2 hub matching.
        existing_orders: list of already-assigned orders on the same (city, delivery_day),
            each with: assigned_courier_id, delivery_day, receipt_lat_wgs84,
            receipt_lon_wgs84, lat_wgs84, lon_wgs84.
        pickup_hub_name: the from_hub_name of the new order, used for tier-2 hub matching.

    Returns:
        (chosen_courier_dict, distance_m_from_pickup)

    Raises:
        ValueError: if no eligible courier can be found.
    """
    nearby_km = NEARBY_HUB_KM
    couriers_by_id = {c["courier_id"]: c for c in couriers}
    order_counts = _count_orders_per_courier(existing_orders, delivery_day)

    # Tier 1: consolidation — courier already has a nearby same-day stop and is under cap
    courier_min_dist: dict[str, float] = {}
    for order in existing_orders:
        if order.get("delivery_day") != delivery_day:
            continue
        cid = order.get("assigned_courier_id")
        if not cid or cid not in couriers_by_id:
            continue
        if order_counts.get(cid, 0) >= MAX_ORDERS_PER_DAY:
            continue

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

    # Tier 2: hub-scoped fallback — courier assigned to the pickup hub, under cap, nearest
    def _dist_to_pickup(courier: dict[str, Any]) -> float:
        return haversine_distance_m(
            pickup_lat,
            pickup_lon,
            float(courier["start_lat_wgs84"]),
            float(courier["start_lon_wgs84"]),
        )

    if pickup_hub_name:
        hub_eligible = [
            c for c in couriers
            if c.get("hub_name") == pickup_hub_name
            and order_counts.get(c["courier_id"], 0) < MAX_ORDERS_PER_DAY
        ]
        if hub_eligible:
            best = min(hub_eligible, key=_dist_to_pickup)
            return best, _dist_to_pickup(best)

    # Final fallback: any active courier in the city under cap, nearest
    cap_eligible = [
        c for c in couriers
        if order_counts.get(c["courier_id"], 0) < MAX_ORDERS_PER_DAY
    ]
    if not cap_eligible:
        raise ValueError(
            "No available courier found: all couriers have reached the daily order limit "
            f"of {MAX_ORDERS_PER_DAY}."
        )

    best = min(cap_eligible, key=_dist_to_pickup)
    return best, _dist_to_pickup(best)
