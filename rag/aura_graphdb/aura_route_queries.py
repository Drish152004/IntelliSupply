from aura_graphdb.aura_connection import AuraConnection


def get_order_route(order_id: str):
    conn = AuraConnection()

    query = """
    MATCH (o:Order {order_id: $order_id})
    OPTIONAL MATCH (o)-[:FROM_HUB]->(fromHub:Hub)
    OPTIONAL MATCH (o)-[:TO_HUB]->(toHub:Hub)
    OPTIONAL MATCH (o)-[:ASSIGNED_TO]->(courier:Courier)
    OPTIONAL MATCH (o)-[:HAS_NOTES]->(notes:Notes)

    RETURN
        o.order_id AS order_id,
        o.city_name AS city_name,
        o.ds AS ds,
        o.delivery_day AS delivery_day,
        o.receipt_time AS receipt_time,

        fromHub.name AS from_hub_name,
        fromHub.latitude AS from_lat,
        fromHub.longitude AS from_lon,

        toHub.name AS to_hub_name,
        toHub.latitude AS to_lat,
        toHub.longitude AS to_lon,

        courier.courier_id AS assigned_courier_id,
        courier.name AS assigned_courier_name,
        courier.email AS assigned_courier_email,

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


def get_recent_order_routes(limit: int = 20):
    conn = AuraConnection()

    query = """
    MATCH (o:Order)
    OPTIONAL MATCH (o)-[:FROM_HUB]->(fromHub:Hub)
    OPTIONAL MATCH (o)-[:TO_HUB]->(toHub:Hub)
    OPTIONAL MATCH (o)-[:ASSIGNED_TO]->(courier:Courier)

    RETURN
        o.order_id AS order_id,
        o.city_name AS city_name,
        o.delivery_day AS delivery_day,
        o.receipt_time AS receipt_time,

        fromHub.name AS from_hub_name,
        fromHub.latitude AS from_lat,
        fromHub.longitude AS from_lon,

        toHub.name AS to_hub_name,
        toHub.latitude AS to_lat,
        toHub.longitude AS to_lon,

        courier.courier_id AS assigned_courier_id,
        courier.name AS assigned_courier_name,

        o.nearest_courier_distance_m AS nearest_courier_distance_m
    ORDER BY o.created_at DESC
    LIMIT $limit
    """

    try:
        return conn.execute_query(query, {"limit": int(limit)})

    finally:
        conn.close()


def get_orders_for_courier_day(
    courier_id: str,
    city_name: str,
    ds: int,
    delivery_day: str,
):
    """Fetch all orders for a courier on a given day (for ML route prediction)."""
    conn = AuraConnection()

    query = """
    MATCH (courier:Courier {courier_id: $courier_id})<-[:ASSIGNED_TO]-(o:Order)
    WHERE o.city_name = $city_name
      AND o.ds = $ds
      AND o.delivery_day = $delivery_day
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
        o.receipt_lon_wgs84 AS receipt_lon_wgs84
    ORDER BY o.created_at
    """

    try:
        return conn.execute_query(
            query,
            {
                "courier_id": courier_id,
                "city_name": city_name,
                "ds": int(ds),
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
        fromHub.latitude AS from_lat,
        fromHub.longitude AS from_lon,

        toHub.name AS to_hub_name,
        toHub.latitude AS to_lat,
        toHub.longitude AS to_lon,

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
                "limit": int(limit)
            }
        )

    finally:
        conn.close()


def answer_route_question(question: str):
    """
    Simple chatbot helper for route/order questions.
    Later this can be replaced with LLM-to-Cypher.
    """

    q = question.lower()

    # Example: "show route for order ord-abc123"
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
                "data": None
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
            "data": route
        }

    if "recent" in q or "latest" in q or "all orders" in q:
        routes = get_recent_order_routes(limit=10)

        return {
            "success": True,
            "answer": f"Found {len(routes)} recent order routes.",
            "data": routes
        }

    return {
        "success": False,
        "answer": "Please provide an order ID, for example: show route for order ord-xxxx.",
        "data": None
    }


if __name__ == "__main__":
    print(get_recent_order_routes())