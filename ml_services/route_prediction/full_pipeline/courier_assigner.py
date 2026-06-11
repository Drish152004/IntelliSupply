"""Courier assignment for the offline batch demo pipeline.

Uses the same shared logic as live ops (courier_assignment.select_courier_for_order):
  - Tier 1: consolidation — prefer courier with a same-day stop within NEARBY_HUB_KM
  - Tier 2: nearest active courier to pickup hub

No cluster CSVs or DBSCAN required.
"""

from __future__ import annotations

from dataclasses import dataclass

from aura_graphdb.courier_assignment import select_courier_for_order


@dataclass
class CourierAssignment:
    order_id: str
    courier_id: str
    city_name: str
    delivery_day: str
    from_hub_name: str
    assignment_dist_m: float


class CourierAssigner:
    """Stateful batch assignment mirroring live FastAPI shipment create."""

    def assign_batch(
        self,
        orders: list[dict],
        couriers: list[dict],
    ) -> list[CourierAssignment]:
        """Assign couriers to all orders in arrival order.

        Each order in `orders` must have:
            order_id, receipt_lat_wgs84, receipt_lon_wgs84,
            lat_wgs84, lon_wgs84, city_name, delivery_day,
            from_hub_name (optional label for output)

        Each courier in `couriers` must have:
            courier_id, start_lat_wgs84, start_lon_wgs84, city_name
        """
        results: list[CourierAssignment] = []
        assigned_so_far: list[dict] = []

        for order in orders:
            city_name = order.get("city_name", "")
            delivery_day = str(order.get("delivery_day", ""))
            pickup_lat = float(order.get("receipt_lat_wgs84") or order.get("lat_wgs84", 0))
            pickup_lon = float(order.get("receipt_lon_wgs84") or order.get("lon_wgs84", 0))

            city_couriers = [c for c in couriers if c.get("city_name") == city_name]
            if not city_couriers:
                city_couriers = couriers

            chosen, dist_m = select_courier_for_order(
                pickup_lat=pickup_lat,
                pickup_lon=pickup_lon,
                delivery_day=delivery_day,
                couriers=city_couriers,
                existing_orders=assigned_so_far,
            )

            results.append(CourierAssignment(
                order_id=order["order_id"],
                courier_id=chosen["courier_id"],
                city_name=city_name,
                delivery_day=delivery_day,
                from_hub_name=order.get("from_hub_name", ""),
                assignment_dist_m=dist_m,
            ))

            assigned_so_far.append({
                "assigned_courier_id": chosen["courier_id"],
                "delivery_day": delivery_day,
                "receipt_lat_wgs84": order.get("receipt_lat_wgs84"),
                "receipt_lon_wgs84": order.get("receipt_lon_wgs84"),
                "lat_wgs84": order.get("lat_wgs84"),
                "lon_wgs84": order.get("lon_wgs84"),
            })

        return results

    def group_by_courier_day(
        self, assignments: list[CourierAssignment]
    ) -> dict[tuple[str, str, str], list[str]]:
        """One route per (courier_id, city_name, delivery_day)."""
        grouped: dict[tuple[str, str, str], list[str]] = {}
        for a in assignments:
            key = (a.courier_id, a.city_name, a.delivery_day)
            grouped.setdefault(key, []).append(a.order_id)
        return grouped
