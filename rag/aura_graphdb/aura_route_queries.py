import json
import math
from typing import Any

from aura_graphdb.aura_connection import AuraConnection
from aura_graphdb.aura_courier import resolve_courier
from aura_graphdb.aura_hubs import resolve_hub

def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _estimate_leg_minutes(order: dict[str, Any], default_minutes: float = 20.0) -> float:
    from_lat = _float_or_none(order.get("from_lat"))
    from_lon = _float_or_none(order.get("from_lon"))
    to_lat = _float_or_none(order.get("to_lat"))
    to_lon = _float_or_none(order.get("to_lon"))
    if from_lat is None or from_lon is None:
        from_lat = _float_or_none(order.get("receipt_lat_wgs84"))
        from_lon = _float_or_none(order.get("receipt_lon_wgs84"))
    if to_lat is None or to_lon is None:
        to_lat = _float_or_none(order.get("lat_wgs84"))
        to_lon = _float_or_none(order.get("lon_wgs84"))
    if None in (from_lat, from_lon, to_lat, to_lon):
        return default_minutes
    km = _haversine_km(from_lat, from_lon, to_lat, to_lon)
    return max(default_minutes, round(km * 3.0, 1))

def get_orders_for_courier_name_day(
    courier_name: str,
    delivery_day: str,
) -> dict:
    courier = resolve_courier(courier_name=courier_name)

    if not courier:
        return {
            "success": False,
            "message": f"No courier found with name {courier_name}.",
            "courier": None,
            "orders": [],
        }

    orders = get_orders_for_courier_day(
        courier_id=courier["courier_id"],
        city_name=courier.get("city_name") or "",
        delivery_day=delivery_day,
    )

    return {
        "success": True,
        "courier": courier,
        "orders": orders,
    }
def resolve_route_hubs(
    from_hub_name: str,
    to_hub_name: str,
) -> dict:
    from_hub = resolve_hub(hub_name=from_hub_name)
    to_hub = resolve_hub(hub_name=to_hub_name)

    if not from_hub:
        return {
            "success": False,
            "message": f"From hub not found: {from_hub_name}",
        }

    if not to_hub:
        return {
            "success": False,
            "message": f"To hub not found: {to_hub_name}",
        }

    return {
        "success": True,
        "from_hub": from_hub,
        "to_hub": to_hub,
    }
def build_route_stops_from_orders(
    orders: list[dict[str, Any]],
    courier: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build ordered route stops from assigned orders without ML."""
    if not orders:
        return {
            "order_ids": [],
            "predicted_sequence": [],
            "stops": [],
            "geo_stops": [],
            "total_eta_minutes": 0.0,
            "city_name": None,
        }

    def sort_key(order: dict[str, Any]) -> tuple:
        seq = order.get("route_sequence")
        if seq is not None:
            try:
                return (0, int(seq))
            except (TypeError, ValueError):
                pass
        receipt = str(order.get("receipt_time") or "")
        return (1, receipt, str(order.get("order_id") or ""))

    ordered = sorted(orders, key=sort_key)
    predicted_sequence = [o["order_id"] for o in ordered if o.get("order_id")]

    cumulative = 0.0
    stops: list[dict[str, Any]] = []
    geo_stops: list[dict[str, Any]] = []

    for seq, order in enumerate(ordered, start=1):
        leg_minutes = _estimate_leg_minutes(order)
        cumulative += leg_minutes
        from_lat = _float_or_none(order.get("from_lat"))
        from_lng = _float_or_none(order.get("from_lon")) or _float_or_none(order.get("from_lng"))
        to_lat = _float_or_none(order.get("to_lat"))
        to_lng = _float_or_none(order.get("to_lon")) or _float_or_none(order.get("to_lng"))
        lat_wgs84 = _float_or_none(order.get("lat_wgs84")) or to_lat
        lon_wgs84 = _float_or_none(order.get("lon_wgs84")) or to_lng

        stops.append(
            {
                "sequence": seq,
                "order_id": order["order_id"],
                "from_hub_name": order.get("from_hub_name"),
                "to_hub_name": order.get("to_hub_name"),
                "from_lat": from_lat,
                "from_lng": from_lng,
                "to_lat": to_lat,
                "to_lng": to_lng,
                "lat_wgs84": lat_wgs84,
                "lon_wgs84": lon_wgs84,
                "city_name": order.get("city_name"),
                "delivery_day": order.get("delivery_day"),
                "eta_minutes": round(leg_minutes, 1),
                "eta_from_start_minutes": round(cumulative, 1),
                "estimated_arrival": f"{int(9 + cumulative // 60):02d}:{int(cumulative % 60):02d}",
            }
        )
        geo_stops.append(
            {
                "sequence": seq,
                "order_id": order["order_id"],
                "lat_wgs84": lat_wgs84,
                "lon_wgs84": lon_wgs84,
            }
        )

    return {
        "order_ids": predicted_sequence,
        "predicted_sequence": predicted_sequence,
        "stops": stops,
        "geo_stops": geo_stops,
        "total_eta_minutes": round(cumulative, 1),
        "city_name": ordered[0].get("city_name"),
    }


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
    MATCH (o:Order)
    WHERE toLower(o.order_id) = toLower($order_id)
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


def get_route_between_hubs(from_hub_id: int, to_hub_id: int):
    """Fetch direct hub-to-hub route metadata from CONNECTED_TO edges."""
    conn = AuraConnection()
    query = """
    MATCH (fromHub:Hub {hub_id: $from_hub_id})-[rel:CONNECTED_TO]->(toHub:Hub {hub_id: $to_hub_id})
    OPTIONAL MATCH (fromHub)-[:LOCATED_IN]->(city:City)
    RETURN
        fromHub.hub_id AS from_hub_id,
        coalesce(fromHub.name, fromHub.hub_name) AS from_hub_name,
        toHub.hub_id AS to_hub_id,
        coalesce(toHub.name, toHub.hub_name) AS to_hub_name,
        city.city_name AS city_name,
        rel.raw_distance_km AS raw_distance_km,
        rel.map_distance_km AS map_distance_km,
        rel.estimated_time_min AS estimated_time_min
    LIMIT 1
    """
    try:
        rows = conn.execute_query(
            query,
            {"from_hub_id": int(from_hub_id), "to_hub_id": int(to_hub_id)},
        )
        return rows[0] if rows else None
    finally:
        conn.close()


def get_recent_order_routes(
    limit: int = 20,
    courier_id: str | None = None,
    delivery_day: str | None = None,
):
    conn = AuraConnection()

    params: dict = {"limit": int(limit)}
    match_parts = ["MATCH (o:Order)"]
    where_clauses: list[str] = []

    if delivery_day:
        where_clauses.append("o.delivery_day = $delivery_day")
        params["delivery_day"] = delivery_day

    if where_clauses:
        match_parts.append("WHERE " + " AND ".join(where_clauses))

    if courier_id:
        match_parts.append(
            "MATCH (o)-[:ASSIGNED_TO]->(courier:Courier {courier_id: $courier_id})"
        )
        params["courier_id"] = courier_id
    else:
        match_parts.append("OPTIONAL MATCH (o)-[:ASSIGNED_TO]->(courier:Courier)")

    query = f"""
    {' '.join(match_parts)}
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


def list_delivery_days_with_orders(limit: int = 30) -> list[str]:
    """Return distinct delivery days that have orders, newest first."""
    conn = AuraConnection()

    query = """
    MATCH (o:Order)
    WHERE o.delivery_day IS NOT NULL
    RETURN DISTINCT o.delivery_day AS delivery_day
    ORDER BY delivery_day DESC
    LIMIT $limit
    """

    try:
        rows = conn.execute_query(query, {"limit": int(limit)})
        return [str(row["delivery_day"]) for row in (rows or []) if row.get("delivery_day")]
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
    WHERE o.delivery_day = $delivery_day
      AND ($city_name = '' OR o.city_name = $city_name)
    OPTIONAL MATCH (o)-[:FROM_HUB]->(fromHub:Hub)
    OPTIONAL MATCH (o)-[:TO_HUB]->(toHub:Hub)

    RETURN
        o.order_id AS order_id,
        o.route_sequence AS route_sequence,
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
                "city_name": city_name or "",
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
       OR (rp.delivery_day = $delivery_day AND rp.courier_id = $courier_id)
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
            from_lat: fromHub.lat,
            from_lng: fromHub.lng,
            to_lat: toHub.lat,
            to_lng: toHub.lng,
            lat_wgs84: coalesce(rel.lat_wgs84, order.lat_wgs84),
            lon_wgs84: coalesce(rel.lon_wgs84, order.lon_wgs84),
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
        graph_stops = [
            s for s in (row.get("graph_stops") or [])
            if s.get("order_id")
        ]
        stops_json = row.get("stops_json")
        display_stops: list[dict] = []
        if stops_json:
            try:
                display_stops = json.loads(stops_json)
            except json.JSONDecodeError:
                display_stops = []

        if display_stops:
            geo_by_order = {s["order_id"]: s for s in graph_stops if s.get("order_id")}
            stops = []
            for stop in display_stops:
                merged = dict(stop)
                geo = geo_by_order.get(stop.get("order_id"), {})
                for key in (
                    "from_lat", "from_lng", "to_lat", "to_lng",
                    "lat_wgs84", "lon_wgs84", "from_hub_name", "to_hub_name",
                ):
                    if merged.get(key) in (None, "", 0) and geo.get(key) not in (None, ""):
                        merged[key] = geo.get(key)
                stops.append(merged)
        else:
            stops = graph_stops

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

        courier = None
        try:
            from aura_graphdb.aura_courier import get_courier_by_id

            courier = get_courier_by_id(courier_id)
        except Exception:
            courier = None
        courier_start = None
        if courier:
            start_lat = courier.get("start_lat_wgs84")
            start_lng = courier.get("start_lon_wgs84")
            if start_lat is not None and start_lng is not None:
                courier_start = {
                    "lat": float(start_lat),
                    "lng": float(start_lng),
                    "name": courier.get("name") or courier_id,
                }

        return {
            "route_prediction_id": row.get("route_prediction_id"),
            "courier_id": courier_id,
            "courier_name": row.get("courier_name"),
            "delivery_day": delivery_day,
            "predicted_sequence": predicted_sequence,
            "stops": stops,
            "total_eta_minutes": float(row["predicted_eta_min"]) if row.get("predicted_eta_min") is not None else None,
            "route_start_time": route_start_time,
            "courier_start": courier_start,
            "source": "graphdb",
        }
    finally:
        conn.close()

