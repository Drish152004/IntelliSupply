"""Order graph operations in Neo4j Aura."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from aura_graphdb.aura_connection import AuraConnection
from aura_graphdb.courier_assignment import select_courier_for_order
from aura_graphdb.hub_coordinates import ML_DEFAULT_DS
from rag.supabase.supabase_notifications import create_notification


def _safe_create_notification(**kwargs):
    try:
        create_notification(**kwargs)
    except Exception as exc:
        print(f"Notification create failed: {exc}")


def create_order_and_assign_nearest_courier(
    from_hub_name: str,
    to_hub_name: str,
    delivery_day: str,
    receipt_time: str,
    typecode: Optional[str] = None,
    aoi_id: Optional[str] = None,
    extra_notes: Optional[str] = None,
):
    """Create a new order and assign it via nearby-hub + same-day courier selection."""
    order_id = f"ord-{uuid.uuid4().hex[:12]}"
    notes_id = f"note-{uuid.uuid4().hex[:12]}"
    conn = AuraConnection()

    lookup_query = """
    MATCH (from_hub:Hub {name: $from_hub_name})-[:LOCATED_IN]->(city:City)
    MATCH (to_hub:Hub {name: $to_hub_name})-[:LOCATED_IN]->(city)

    MATCH (courier:Courier)-[:OPERATES_IN]->(city)
    WHERE courier.is_active = true
      AND courier.start_lat_wgs84 IS NOT NULL
      AND courier.start_lon_wgs84 IS NOT NULL

    RETURN
        city.city_name AS city_name,
        from_hub.name AS from_hub_name,
        from_hub.hub_id AS from_hub_id,
        from_hub.lat_wgs84 AS from_lat,
        from_hub.lon_wgs84 AS from_lon,
        to_hub.name AS to_hub_name,
        to_hub.hub_id AS to_hub_id,
        to_hub.lat_wgs84 AS to_lat,
        to_hub.lon_wgs84 AS to_lon,
        to_hub.typecode AS to_typecode,
        to_hub.aoi_id AS to_aoi_id,
        courier.courier_id AS courier_id,
        courier.profile_id AS profile_id,
        courier.name AS courier_name,
        courier.start_lat_wgs84 AS courier_lat,
        courier.start_lon_wgs84 AS courier_lon
    """

    existing_orders_query = """
    MATCH (o:Order)-[:ASSIGNED_TO]->(courier:Courier)-[:OPERATES_IN]->(city:City {city_name: $city_name})
    WHERE o.delivery_day = $delivery_day
    RETURN
        o.assigned_courier_id AS assigned_courier_id,
        o.delivery_day AS delivery_day,
        o.receipt_lat_wgs84 AS receipt_lat_wgs84,
        o.receipt_lon_wgs84 AS receipt_lon_wgs84,
        o.lat_wgs84 AS lat_wgs84,
        o.lon_wgs84 AS lon_wgs84
    """

    write_query = """
    MATCH (from_hub:Hub {name: $from_hub_name})-[:LOCATED_IN]->(city:City)
    MATCH (to_hub:Hub {name: $to_hub_name})-[:LOCATED_IN]->(city)
    MATCH (courier:Courier {courier_id: $courier_id})-[:OPERATES_IN]->(city)

    CREATE (order:Order {
        order_id: $order_id,
        lat_wgs84: toFloat($to_lat),
        lon_wgs84: toFloat($to_lon),
        city_name: city.city_name,
        ds: toInteger($ds),
        delivery_day: $delivery_day,
        receipt_time: $receipt_time,
        typecode: coalesce($typecode, to_hub.typecode),
        aoi_id: coalesce($aoi_id, to_hub.aoi_id),
        receipt_lat_wgs84: toFloat($from_lat),
        receipt_lon_wgs84: toFloat($from_lon),
        from_hub_name: from_hub.name,
        to_hub_name: to_hub.name,
        assigned_courier_id: courier.courier_id,
        nearest_courier_distance_m: toFloat($distance_m),
        created_at: datetime(),
        updated_at: datetime()
    })

    CREATE (notes:Notes {
        notes_id: $notes_id,
        text: CASE
            WHEN $notes_text IS NOT NULL AND trim($notes_text) <> ""
            THEN $notes_text
            ELSE "from=" + from_hub.name + "; to=" + to_hub.name + "; courier=" + substring(courier.courier_id, 0, 8)
        END,
        courier_id: courier.courier_id,
        created_at: datetime()
    })

    MERGE (order)-[:FROM_HUB]->(from_hub)
    MERGE (order)-[:TO_HUB]->(to_hub)
    MERGE (order)-[:BELONGS_TO_CITY]->(city)
    MERGE (order)-[:ASSIGNED_TO]->(courier)
    MERGE (order)-[:HAS_NOTES]->(notes)

    RETURN
        order.order_id AS order_id,
        order.lat_wgs84 AS lat_wgs84,
        order.lon_wgs84 AS lon_wgs84,
        order.city_name AS city_name,
        order.ds AS ds,
        order.delivery_day AS delivery_day,
        order.receipt_time AS receipt_time,
        order.typecode AS typecode,
        order.aoi_id AS aoi_id,
        order.receipt_lat_wgs84 AS receipt_lat_wgs84,
        order.receipt_lon_wgs84 AS receipt_lon_wgs84,
        notes.text AS notes,
        courier.courier_id AS assigned_courier_id,
        courier.profile_id AS assigned_courier_profile_id,
        courier.name AS assigned_courier_name,
        $distance_m AS nearest_courier_distance_m,
        from_hub.name AS from_hub_name,
        to_hub.name AS to_hub_name
    """

    params = {
        "from_hub_name": from_hub_name.strip(),
        "to_hub_name": to_hub_name.strip(),
        "ds": ML_DEFAULT_DS,
    }

    try:
        candidates = conn.execute_query(lookup_query, params)
        if not candidates:
            return {
                "success": False,
                "message": (
                    "Could not create order. Check that both hubs exist in the same city "
                    "and at least one active courier is available."
                ),
            }

        first = candidates[0]
        from_lat = float(first["from_lat"])
        from_lon = float(first["from_lon"])
        to_lat = float(first["to_lat"])
        to_lon = float(first["to_lon"])
        city_name = first["city_name"]

        seen_courier_ids: set[str] = set()
        couriers = []
        for c in candidates:
            if c["courier_id"] in seen_courier_ids:
                continue
            seen_courier_ids.add(c["courier_id"])
            couriers.append({
                "courier_id": c["courier_id"],
                "profile_id": c["profile_id"],
                "name": c["courier_name"],
                "start_lat_wgs84": float(c["courier_lat"]),
                "start_lon_wgs84": float(c["courier_lon"]),
                "city_name": city_name,
            })

        existing_orders = conn.execute_query(
            existing_orders_query,
            {"city_name": city_name, "delivery_day": delivery_day},
        )

        nearest_courier, distance_m = select_courier_for_order(
            pickup_lat=from_lat,
            pickup_lon=from_lon,
            delivery_day=delivery_day,
            couriers=couriers,
            existing_orders=[dict(o) for o in (existing_orders or [])],
        )

        result = conn.execute_write(
            write_query,
            {
                **params,
                "order_id": order_id,
                "notes_id": notes_id,
                "delivery_day": delivery_day,
                "receipt_time": receipt_time,
                "typecode": typecode,
                "aoi_id": aoi_id,
                "notes_text": extra_notes or "",
                "courier_id": nearest_courier["courier_id"],
                "from_lat": from_lat,
                "from_lon": from_lon,
                "to_lat": to_lat,
                "to_lon": to_lon,
                "distance_m": distance_m,
            },
        )

        if not result:
            return {
                "success": False,
                "message": "Order write failed after courier selection.",
            }

        order = result[0]

        for role in ["admin", "logistics_manager"]:
            _safe_create_notification(
                title="New shipment created",
                message=(
                    f"Order {order['order_id']} was created from {order['from_hub_name']} "
                    f"to {order['to_hub_name']} and assigned to {order['assigned_courier_name']}."
                ),
                alert_type="order_created",
                severity="medium",
                target_role=role,
                related_entity_type="order",
                related_entity_id=order["order_id"],
                source="graphdb",
            )

        if order.get("assigned_courier_profile_id"):
            _safe_create_notification(
                title="New order assigned",
                message=(
                    f"You have been assigned order {order['order_id']} from "
                    f"{order['from_hub_name']} to {order['to_hub_name']}."
                ),
                alert_type="order_assigned",
                severity="medium",
                target_user_id=order["assigned_courier_profile_id"],
                related_entity_type="order",
                related_entity_id=order["order_id"],
                source="graphdb",
            )

        return {
            "success": True,
            "message": "Order created and assigned successfully.",
            "order": order,
        }
    finally:
        conn.close()
