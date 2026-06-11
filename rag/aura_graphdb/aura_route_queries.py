import json
from typing import Any

from aura_graphdb.aura_connection import AuraConnection


def _format_datetime_value(value: Any) -> str:
    """Normalize Neo4j DateTime or Python datetime to a display string."""
    if hasattr(value, "iso_format"):
        return value.iso_format()
    if hasattr(value, "isoformat"):
        return value.isoformat(sep=" ")
    return str(value)


def get_order_route(order_id: str):
    conn = AuraConnection()

    query = """
    MATCH (o:Order {order_id: $order_id})
    OPTIONAL MATCH (o)-[:FROM_HUB]->(fromHub:Hub)
    OPTIONAL MATCH (o)-[:TO_HUB]->(toHub:Hub)
    OPTIONAL MATCH (o)-[:ASSIGNED_TO]->(courier:Courier)
    OPTIONAL MATCH (courier)-[:ASSIGNED_TO_HUB]->(courierHub:Hub)
    OPTIONAL MATCH (o)-[:HAS_NOTES]->(notes:Notes)

    RETURN
        o.order_id AS order_id,
        o.city_name AS city_name,
        o.ds AS ds,
        o.delivery_day AS delivery_day,
        o.receipt_time AS receipt_time,

        fromHub.name AS from_hub_name,
        fromHub.lat AS from_lat,
        fromHub.lng AS from_lon,

        toHub.name AS to_hub_name,
        toHub.lat AS to_lat,
        toHub.lng AS to_lon,

        courier.courier_id AS assigned_courier_id,
        courier.name AS assigned_courier_name,
        courier.email AS assigned_courier_email,
        coalesce(courierHub.name, courier.hub_name) AS assigned_courier_hub_name,

        o.nearest_courier_distance_m AS nearest_courier_distance_m,
        o.typecode AS typecode,
        o.aoi_id AS aoi_id,
        notes.text AS notes
    LIMIT 1
    """

    try:
        result = conn.execute_query(query, {"order_id": order_id})
        return result[0] if result else None
    finally:
        conn.close()


def get_recent_order_routes(
    limit: int = 20,
    courier_id: str | None = None,
    delivery_day: str | None = None,
):
    conn = AuraConnection()

    params: dict = {"limit": int(limit)}

    # Filter on Order/Courier before hub OPTIONAL MATCHes — WHERE after OPTIONAL MATCH
    # does not reliably constrain o.delivery_day or courier.courier_id in Aura.
    if courier_id:
        courier_match = (
            "MATCH (o)-[:ASSIGNED_TO]->(courier:Courier {courier_id: $courier_id})"
        )
        params["courier_id"] = courier_id
    else:
        courier_match = "OPTIONAL MATCH (o)-[:ASSIGNED_TO]->(courier:Courier)"

    where_clauses = []
    if delivery_day:
        where_clauses.append("o.delivery_day = $delivery_day")
        params["delivery_day"] = delivery_day

    where_str = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    query = f"""
    MATCH (o:Order)
    {courier_match}
    {where_str}
    WITH o, courier
    OPTIONAL MATCH (o)-[:FROM_HUB]->(fromHub:Hub)
    OPTIONAL MATCH (o)-[:TO_HUB]->(toHub:Hub)

    RETURN
        o.order_id AS order_id,
        o.city_name AS city_name,
        o.delivery_day AS delivery_day,
        o.receipt_time AS receipt_time,

        fromHub.name AS from_hub_name,
        fromHub.lat AS from_lat,
        fromHub.lng AS from_lon,

        toHub.name AS to_hub_name,
        toHub.lat AS to_lat,
        toHub.lng AS to_lon,

        courier.courier_id AS assigned_courier_id,
        courier.name AS assigned_courier_name,

        o.nearest_courier_distance_m AS nearest_courier_distance_m
    ORDER BY o.created_at DESC
    LIMIT $limit
    """

    try:
        return conn.execute_query(query, params)
    finally:
        conn.close()


def get_orders_for_courier_day(
    courier_id: str,
    city_name: str,
    delivery_day: str,
):
    """Fetch all orders for a courier on a given delivery day for ML route prediction."""
    conn = AuraConnection()

    query = """
    MATCH (courier:Courier {courier_id: $courier_id})<-[:ASSIGNED_TO]-(o:Order)
    WHERE o.city_name = $city_name
      AND o.delivery_day = $delivery_day
    OPTIONAL MATCH (o)-[:FROM_HUB]->(fromHub:Hub)
    OPTIONAL MATCH (o)-[:TO_HUB]->(toHub:Hub)

    RETURN
        o.order_id AS order_id,
        o.lat_wgs84 AS lat_wgs84,
        o.lon_wgs84 AS lon_wgs84,
        o.city_name AS city_name,
        o.ds AS ds,
        o.delivery_day AS delivery_day,
        o.receipt_time AS receipt_time,
        o.typecode AS typecode,
        o.aoi_id AS aoi_id,
        o.receipt_lat_wgs84 AS receipt_lat_wgs84,
        o.receipt_lon_wgs84 AS receipt_lon_wgs84,
        fromHub.name AS from_hub_name,
        fromHub.lat AS from_lat,
        fromHub.lng AS from_lon,
        toHub.name AS to_hub_name,
        toHub.lat AS to_lat,
        toHub.lng AS to_lon
    ORDER BY o.created_at
    """

    try:
        return conn.execute_query(
            query,
            {
                "courier_id": courier_id,
                "city_name": city_name,
                "delivery_day": delivery_day,
            },
        )
    finally:
        conn.close()


def get_orders_for_courier(courier_id: str, limit: int = 20):
    conn = AuraConnection()

    query = """
    MATCH (courier:Courier {courier_id: $courier_id})<-[:ASSIGNED_TO]-(o:Order)
    OPTIONAL MATCH (o)-[:FROM_HUB]->(fromHub:Hub)
    OPTIONAL MATCH (o)-[:TO_HUB]->(toHub:Hub)

    RETURN
        o.order_id AS order_id,
        o.city_name AS city_name,
        o.delivery_day AS delivery_day,
        o.receipt_time AS receipt_time,

        fromHub.name AS from_hub_name,
        fromHub.lat AS from_lat,
        fromHub.lng AS from_lon,

        toHub.name AS to_hub_name,
        toHub.lat AS to_lat,
        toHub.lng AS to_lon,

        courier.courier_id AS assigned_courier_id,
        courier.name AS assigned_courier_name,

        o.nearest_courier_distance_m AS nearest_courier_distance_m
    ORDER BY o.created_at DESC
    LIMIT $limit
    """

    try:
        return conn.execute_query(
            query,
            {
                "courier_id": courier_id,
                "limit": int(limit),
            },
        )
    finally:
        conn.close()


def get_saved_courier_route(
    courier_id: str,
    delivery_day: str,
    ds: int = 318,
) -> dict | None:
    """Load a persisted RoutePrediction for a courier on a delivery day."""
    conn = AuraConnection()
    route_prediction_ids = [
        f"{courier_id}_{ds}_{delivery_day}",
        f"{courier_id}_{delivery_day}",
    ]

    query = """
    MATCH (rp:RoutePrediction)-[:FOR_COURIER]->(courier:Courier {courier_id: $courier_id})
    WHERE rp.route_prediction_id IN $route_prediction_ids
       OR rp.delivery_day = $delivery_day
    WITH rp, courier
    ORDER BY rp.updated_at DESC
    LIMIT 1

    OPTIONAL MATCH (rp)-[rel:HAS_STOP]->(order:Order)
    OPTIONAL MATCH (order)-[:FROM_HUB]->(fromHub:Hub)
    OPTIONAL MATCH (order)-[:TO_HUB]->(toHub:Hub)
    WITH rp, courier, rel, order, fromHub, toHub
    ORDER BY rel.sequence
    WITH rp, courier,
         collect({
            sequence: rel.sequence,
            order_id: order.order_id,
            from_hub_name: coalesce(order.from_hub_name, fromHub.name),
            to_hub_name: coalesce(order.to_hub_name, toHub.name),
            city_name: order.city_name,
            delivery_day: order.delivery_day
         }) AS graph_stops

    RETURN
        rp.route_prediction_id AS route_prediction_id,
        rp.courier_id AS courier_id,
        rp.delivery_day AS delivery_day,
        rp.predicted_sequence AS predicted_sequence,
        rp.predicted_eta_min AS predicted_eta_min,
        rp.stops_json AS stops_json,
        rp.route_start_time AS route_start_time,
        rp.updated_at AS updated_at,
        courier.name AS courier_name,
        graph_stops
    """

    try:
        rows = conn.execute_query(
            query,
            {
                "courier_id": courier_id,
                "delivery_day": delivery_day,
                "route_prediction_ids": route_prediction_ids,
            },
        )
        if not rows:
            return None

        row = rows[0]
        stops_json = row.get("stops_json")
        if stops_json:
            try:
                stops = json.loads(stops_json)
            except json.JSONDecodeError:
                stops = []
        else:
            stops = [
                s for s in (row.get("graph_stops") or [])
                if s.get("order_id")
            ]

        if not stops:
            return None

        predicted_sequence = row.get("predicted_sequence") or [
            s["order_id"] for s in sorted(stops, key=lambda x: x.get("sequence", 0))
        ]

        route_start_time = row.get("route_start_time")
        if route_start_time is not None and not isinstance(route_start_time, str):
            route_start_time = _format_datetime_value(route_start_time)
        if not route_start_time and row.get("updated_at"):
            route_start_time = _format_datetime_value(row["updated_at"])

        return {
            "route_prediction_id": row.get("route_prediction_id"),
            "courier_id": courier_id,
            "courier_name": row.get("courier_name"),
            "delivery_day": delivery_day,
            "predicted_sequence": predicted_sequence,
            "stops": stops,
            "total_eta_minutes": float(row["predicted_eta_min"]) if row.get("predicted_eta_min") is not None else None,
            "route_start_time": route_start_time,
            "source": "graphdb",
        }
    finally:
        conn.close()


def answer_route_question(question: str):
    """
    Simple chatbot helper for route/order questions.
    Later this can be replaced with LLM-to-Cypher.
    """
    q = question.lower()
    words = question.replace("?", "").replace(",", "").split()

    order_id = None
    for word in words:
        if word.startswith("ord-"):
            order_id = word
            break

    if order_id:
        route = get_order_route(order_id)

        if not route:
            return {
                "success": False,
                "answer": f"No route found for order {order_id}.",
                "data": None,
            }

        answer = (
            f"Order {route['order_id']} goes from {route['from_hub_name']} "
            f"to {route['to_hub_name']} in {route['city_name']}. "
            f"It is assigned to courier {route['assigned_courier_name']} "
            f"({route['assigned_courier_id']})."
        )

        return {
            "success": True,
            "answer": answer,
            "data": route,
        }

    if "recent" in q or "latest" in q or "all orders" in q:
        routes = get_recent_order_routes(limit=10)

        return {
            "success": True,
            "answer": f"Found {len(routes)} recent order routes.",
            "data": routes,
        }

    return {
        "success": False,
        "answer": "Please provide an order ID, for example: show route for order ord-xxxx.",
        "data": None,
    }