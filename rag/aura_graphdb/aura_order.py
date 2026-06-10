"""Order graph operations in Neo4j Aura."""

from __future__ import annotations

import uuid
from typing import Optional

from aura_graphdb.aura_connection import AuraConnection


def create_order_and_assign_nearest_courier(
    from_hub_name: str,
    to_hub_name: str,
    delivery_day: str,
    receipt_time: str,
    ds: int = 318,
    typecode: Optional[str] = None,
    aoi_id: Optional[str] = None,
    extra_notes: Optional[str] = None,
):
    """
    Create a new order and assign it to the nearest active courier.

    The source hub is used as the pickup location.
    The destination hub is used as the delivery location.
    """
    order_id = f"ord-{uuid.uuid4().hex[:12]}"
    notes_id = f"note-{uuid.uuid4().hex[:12]}"

    conn = AuraConnection()

    query = """
    MATCH (from_hub:Hub {name: $from_hub_name})-[:LOCATED_IN]->(city:City)
    MATCH (to_hub:Hub {name: $to_hub_name})-[:LOCATED_IN]->(city)

    MATCH (courier:Courier)-[:OPERATES_IN]->(city)
    WHERE courier.is_active = true
      AND courier.ds = toInteger($ds)
      AND courier.start_lat_wgs84 IS NOT NULL
      AND courier.start_lon_wgs84 IS NOT NULL

    WITH
        from_hub,
        to_hub,
        city,
        courier,
        point.distance(
            point({
                latitude: toFloat(courier.start_lat_wgs84),
                longitude: toFloat(courier.start_lon_wgs84)
            }),
            point({
                latitude: toFloat(from_hub.latitude),
                longitude: toFloat(from_hub.longitude)
            })
        ) AS distance_m

    ORDER BY distance_m ASC
    LIMIT 1

    CREATE (order:Order {
        order_id: $order_id,
        lat_wgs84: toFloat(to_hub.latitude),
        lon_wgs84: toFloat(to_hub.longitude),
        city_name: city.city_name,
        ds: toInteger($ds),
        delivery_day: $delivery_day,
        receipt_time: $receipt_time,
        typecode: coalesce($typecode, to_hub.typecode),
        aoi_id: coalesce($aoi_id, to_hub.aoi_id),
        receipt_lat_wgs84: toFloat(from_hub.latitude),
        receipt_lon_wgs84: toFloat(from_hub.longitude),
        from_hub_name: from_hub.name,
        to_hub_name: to_hub.name,
        assigned_courier_id: courier.courier_id,
        nearest_courier_distance_m: distance_m,
        created_at: datetime(),
        updated_at: datetime()
    })

    CREATE (notes:Notes {
        notes_id: $notes_id,
        text: CASE
            WHEN $notes_text IS NOT NULL AND trim($notes_text) <> ""
            THEN $notes_text
            ELSE "cluster=" + to_hub.name + "; courier=" + substring(courier.courier_id, 0, 8)
        END,
        cluster: toString(to_hub.hub_id),
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
        courier.name AS assigned_courier_name,
        distance_m AS nearest_courier_distance_m,
        from_hub.name AS from_hub_name,
        to_hub.name AS to_hub_name,
        to_hub.hub_id AS cluster_id
    """

    try:
        result = conn.execute_write(
            query,
            {
                "order_id": order_id,
                "notes_id": notes_id,
                "from_hub_name": from_hub_name.strip(),
                "to_hub_name": to_hub_name.strip(),
                "delivery_day": delivery_day,
                "receipt_time": receipt_time,
                "ds": int(ds),
                "typecode": typecode,
                "aoi_id": aoi_id,
                "notes_text": extra_notes or "",
            },
        )

        if not result:
            return {
                "success": False,
                "message": "Could not create order. Check that both hubs exist in the same city and at least one active courier exists.",
            }

        return {
            "success": True,
            "message": "Order created and assigned to nearest courier successfully.",
            "order": result[0],
        }

    finally:
        conn.close()