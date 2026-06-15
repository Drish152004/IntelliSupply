import json
import math
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from aura_graphdb.aura_connection import AuraConnection
from rag.supabase.supabase_connection import get_supabase_engine
from rag.aura_graphdb.shared_cypher import PERSIST_ASSIGNED_ROUTE_QUERY


PIPELINE_DATA_DIR = (
    Path(__file__).resolve().parents[2]
    / "ml_services"
    / "route_prediction"
    / "full_pipeline"
    / "data"
)

PIPELINE_OUTPUT_DIR = (
    Path(__file__).resolve().parents[2]
    / "ml_services"
    / "route_prediction"
    / "full_pipeline"
    / "outputs"
)


# ============================================================
# Utility helpers
# ============================================================

def _safe_float(value, default=None):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    """
    Calculate approximate distance between two WGS84 points.
    Used only to create realistic ETA values for seeded assigned_routes.
    """
    lat1 = _safe_float(lat1)
    lon1 = _safe_float(lon1)
    lat2 = _safe_float(lat2)
    lon2 = _safe_float(lon2)

    if None in [lat1, lon1, lat2, lon2]:
        return 2.0

    radius_km = 6371.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(delta_lambda / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return radius_km * c


def _parse_route_start_time(route: dict) -> datetime:
    """
    Use route_start_time if present.
    Otherwise use delivery_day 08:00:00.
    """
    delivery_day = route.get("delivery_day") or "2026-06-03"

    route_start_time = route.get("route_start_time")
    if route_start_time:
        try:
            return datetime.strptime(route_start_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

    return datetime.strptime(f"{delivery_day} 08:00:00", "%Y-%m-%d %H:%M:%S")


def _enrich_route_for_frontend(route: dict) -> dict:
    """
    Convert seeded assigned_routes.json into the same shape as ML-persisted routes.

    This adds:
    - route_prediction_id
    - predicted_eta_min
    - predicted_stops_json
    - stops_json with ETA fields for frontend
    """
    courier_id = route["courier_id"]
    ds = int(route.get("ds") or 318)
    delivery_day = route.get("delivery_day") or "unknown"

    route["route_prediction_id"] = route.get(
        "route_prediction_id"
    ) or f"{courier_id}_{ds}_{delivery_day}"

    route.pop("cluster_id", None)

    route["ds"] = ds
    route["delivery_day"] = delivery_day
    route["city_name"] = route.get("city_name")
    route["order_ids"] = route.get("order_ids") or []
    route["predicted_sequence"] = route.get("predicted_sequence") or route["order_ids"]

    raw_stops = route.get("stops") or []

    route_start = _parse_route_start_time(route)
    route_start_time = route.get("route_start_time") or route_start.strftime("%Y-%m-%d %H:%M:%S")

    geo_stops = []
    display_stops = []

    cumulative_eta = 0.0
    prev_lat = None
    prev_lon = None

    for index, stop in enumerate(raw_stops, start=1):
        sequence = int(stop.get("sequence") or index)
        order_id = stop.get("order_id")

        lat = _safe_float(stop.get("lat_wgs84"))
        lon = _safe_float(stop.get("lon_wgs84"))

        if prev_lat is None or prev_lon is None:
            distance_km = 2.0
        else:
            distance_km = _haversine_km(prev_lat, prev_lon, lat, lon)

        # Synthetic realistic ETA:
        # city average speed around 22 km/h + 4 min stop/service buffer.
        leg_eta = round(max(6.0, (distance_km / 22.0) * 60.0 + 4.0), 1)

        cumulative_eta += leg_eta
        arrival_time = route_start + timedelta(minutes=cumulative_eta)

        geo_stops.append(
            {
                "sequence": sequence,
                "order_id": order_id,
                "lat_wgs84": lat,
                "lon_wgs84": lon,
            }
        )

        display_stops.append(
            {
                "sequence": sequence,
                "order_id": order_id,
                "from_hub_name": stop.get("from_hub_name"),
                "to_hub_name": stop.get("to_hub_name"),
                "city_name": route.get("city_name"),
                "delivery_day": delivery_day,
                "eta_minutes": leg_eta,
                "eta_from_start_minutes": round(cumulative_eta, 1),
                "estimated_arrival": arrival_time.strftime("%H:%M"),
                "lat_wgs84": lat,
                "lon_wgs84": lon,
            }
        )

        prev_lat = lat
        prev_lon = lon

    route["stops"] = geo_stops
    route["predicted_stops_json"] = json.dumps(geo_stops)
    route["stops_json"] = json.dumps(display_stops)
    route["predicted_eta_min"] = route.get("predicted_eta_min") or round(cumulative_eta, 1)
    route["route_start_time"] = route_start_time

    return route


# ============================================================
# Load cities
# ============================================================

def load_cities_to_aura():
    engine = get_supabase_engine()
    conn = AuraConnection()

    df = pd.read_sql(
        """
        SELECT city_id, city_name
        FROM cities
        ORDER BY city_id
        """,
        engine,
    )

    rows = df.to_dict("records")

    query = """
    UNWIND $rows AS row
    MERGE (c:City {city_id: toInteger(row.city_id)})
    SET c.city_name = row.city_name
    """

    try:
        conn.execute_write(query, {"rows": rows})
        print(f"Loaded {len(rows)} cities into Aura.")
    finally:
        conn.close()


# ============================================================
# Load hubs
# ============================================================

def load_hubs_to_aura():
    """
    Load hubs from Supabase into Aura.
    Hub lat/lng are treated as source of truth for courier start location.
    """
    engine = get_supabase_engine()
    conn = AuraConnection()

    df = pd.read_sql(
        """
        SELECT
            h.hub_id,
            h.hub_name,
            h.city_id,
            h.lat,
            h.lng,
            h.representative_aoi_id,
            h.representative_typecode,
            h.hub_type,
            c.city_name
        FROM hubs h
        JOIN cities c
            ON h.city_id = c.city_id
        ORDER BY h.hub_id
        """,
        engine,
    )

    df = df.where(pd.notnull(df), None)
    rows = df.to_dict("records")

    query = """
    UNWIND $rows AS row

    MERGE (city:City {city_id: toInteger(row.city_id)})
    SET city.city_name = row.city_name

    MERGE (hub:Hub {hub_id: toInteger(row.hub_id)})
    ON CREATE SET hub.created_at = datetime()
    SET
        hub.hub_name = row.hub_name,
        hub.name = row.hub_name,
        hub.lat = toFloat(row.lat),
        hub.lng = toFloat(row.lng),
        hub.representative_aoi_id = row.representative_aoi_id,
        hub.representative_typecode = row.representative_typecode,
        hub.hub_type = row.hub_type,
        hub.city_id = toInteger(row.city_id),
        hub.city_name = row.city_name,
        hub.updated_at = datetime()

    MERGE (hub)-[:LOCATED_IN]->(city)
    """

    try:
        conn.execute_write(query, {"rows": rows})
        print(f"Loaded {len(rows)} hubs into Aura.")
    finally:
        conn.close()


# ============================================================
# Load hub distances
# ============================================================

def load_hub_distances_to_aura():
    """
    Load hub_distances from Supabase as (:Hub)-[:CONNECTED_TO]->(:Hub).

    If the table does not exist in the new Supabase project, skip it.
    """
    engine = get_supabase_engine()
    conn = AuraConnection()

    try:
        df = pd.read_sql(
            """
            SELECT
                from_hub_id,
                to_hub_id,
                city_id,
                raw_distance_km,
                map_distance_km,
                estimated_time_min,
                created_at::text AS created_at
            FROM hub_distances
            ORDER BY from_hub_id, to_hub_id
            """,
            engine,
        )
    except Exception as exc:
        print(f"Skipping hub_distances load: {exc}")
        conn.close()
        return

    df = df.where(pd.notnull(df), None)
    rows = df.to_dict("records")

    query = """
    UNWIND $rows AS row

    MATCH (from_hub:Hub {hub_id: toInteger(row.from_hub_id)})
    MATCH (to_hub:Hub {hub_id: toInteger(row.to_hub_id)})

    MERGE (from_hub)-[rel:CONNECTED_TO]->(to_hub)
    SET
        rel.raw_distance_km = toFloat(row.raw_distance_km),
        rel.map_distance_km = toFloat(row.map_distance_km),
        rel.estimated_time_min = toFloat(row.estimated_time_min),
        rel.city_id = toInteger(row.city_id),
        rel.created_at = row.created_at,
        rel.updated_at = datetime()
    """

    try:
        conn.execute_write(query, {"rows": rows})
        print(f"Loaded {len(rows)} hub distance relationships into Aura.")
    finally:
        conn.close()


# ============================================================
# Load synthetic couriers
# ============================================================

def load_synthetic_couriers_to_aura(json_path="synthetic_couriers.json"):
    """
    Load synthetic couriers.

    Required per courier:
    - courier_id
    - city_name
    - hub_name

    Optional:
    - name
    - email

    Important:
    - Courier start position is always taken from assigned hub lat/lng.
    - Do not use start_lat_wgs84/start_lon_wgs84 from JSON.
    """
    conn = AuraConnection()

    with open(json_path, "r", encoding="utf-8") as file:
        rows = json.load(file)

    missing_hub = [
        row.get("courier_id", "unknown")
        for row in rows
        if not row.get("hub_name")
    ]

    if missing_hub:
        raise ValueError(
            "These synthetic couriers are missing mandatory hub_name: "
            + ", ".join(missing_hub[:20])
        )

    for index, row in enumerate(rows, start=1):
        row.setdefault("name", f"Courier {index}")
        row.setdefault("email", f"courier{index}@intellisupply.local")

    query = """
    UNWIND $rows AS row

    MATCH (city:City {city_name: row.city_name})
    MATCH (hub:Hub {name: row.hub_name})-[:LOCATED_IN]->(city)

    MERGE (role:Role {role_id: 2})
    SET role.role_name = "courier"

    MERGE (courier:Courier {courier_id: row.courier_id})
    ON CREATE SET courier.created_at = datetime()
    SET
        courier.name = row.name,
        courier.email = row.email,
        courier.city_id = city.city_id,
        courier.city_name = row.city_name,
        courier.hub_id = hub.hub_id,
        courier.hub_name = hub.name,
        courier.start_lat_wgs84 = hub.lat,
        courier.start_lon_wgs84 = hub.lng,
        courier.is_active = true,
        courier.updated_at = datetime()

    MERGE (courier)-[:HAS_ROLE]->(role)
    MERGE (courier)-[:OPERATES_IN]->(city)
    MERGE (courier)-[:ASSIGNED_TO_HUB]->(hub)
    """

    try:
        conn.execute_write(query, {"rows": rows})
        print(f"Loaded {len(rows)} synthetic couriers into Aura.")
    finally:
        conn.close()


# ============================================================
# Load synthetic orders
# ============================================================

def load_synthetic_orders_to_aura(json_path="synthetic_orders.json"):
    """
    Load synthetic orders.

    Required per order:
    - order_id
    - city_name
    - ds
    - delivery_day
    - receipt_time
    - typecode
    - aoi_id
    - from_hub_name
    - to_hub_name

    Important:
    - from_hub_name and to_hub_name are mandatory.
    - Order receipt coordinates come from from_hub.
    - Order destination coordinates come from to_hub.
    - Do not silently guess hubs.
    """
    conn = AuraConnection()

    with open(json_path, "r", encoding="utf-8") as file:
        rows = json.load(file)

    missing_hub_orders = [
        row.get("order_id", "unknown")
        for row in rows
        if not row.get("from_hub_name") or not row.get("to_hub_name")
    ]

    if missing_hub_orders:
        raise ValueError(
            "These synthetic orders are missing mandatory from_hub_name/to_hub_name: "
            + ", ".join(missing_hub_orders[:20])
        )

    for row in rows:
        row.setdefault("notes", "")

    query = """
    UNWIND $rows AS row

    MATCH (city:City {city_name: row.city_name})
    MATCH (fromHub:Hub {name: row.from_hub_name})-[:LOCATED_IN]->(city)
    MATCH (toHub:Hub {name: row.to_hub_name})-[:LOCATED_IN]->(city)

    MERGE (order:Order {order_id: row.order_id})
    ON CREATE SET order.created_at = datetime()
    SET
        order.lat_wgs84 = toFloat(toHub.lat),
        order.lon_wgs84 = toFloat(toHub.lng),
        order.city_name = row.city_name,
        order.ds = toInteger(row.ds),
        order.delivery_day = row.delivery_day,
        order.receipt_time = row.receipt_time,
        order.typecode = coalesce(row.typecode, toHub.representative_typecode),
        order.aoi_id = coalesce(row.aoi_id, toHub.representative_aoi_id),
        order.receipt_lat_wgs84 = toFloat(fromHub.lat),
        order.receipt_lon_wgs84 = toFloat(fromHub.lng),
        order.from_hub_name = fromHub.name,
        order.to_hub_name = toHub.name,
        order.notes_text = row.notes,
        order.updated_at = datetime()

    MERGE (notes:Notes {notes_id: "note_" + row.order_id})
    ON CREATE SET notes.created_at = datetime()
    SET
        notes.text = coalesce(row.notes, ""),
        notes.updated_at = datetime()

    MERGE (order)-[:BELONGS_TO_CITY]->(city)
    MERGE (order)-[:HAS_NOTES]->(notes)
    MERGE (order)-[:FROM_HUB]->(fromHub)
    MERGE (order)-[:TO_HUB]->(toHub)
    """

    try:
        conn.execute_write(query, {"rows": rows})
        print(f"Loaded {len(rows)} synthetic orders into Aura.")
    finally:
        conn.close()


# ============================================================
# Load assigned routes
# ============================================================

def load_assigned_routes_to_aura(json_path=None):
    """
    Load assigned routes.

    Required per route:
    - courier_id
    - order_ids
    - predicted_sequence
    - stops
    - ds
    - city_name
    - delivery_day

    This enriches assigned routes with:
    - route_prediction_id
    - predicted_eta_min
    - predicted_stops_json
    - stops_json for frontend display
    """
    conn = AuraConnection()

    if json_path is None:
        json_path = PIPELINE_OUTPUT_DIR / "assigned_routes.json"

    json_path = Path(json_path)

    with open(json_path, "r", encoding="utf-8") as file:
        routes = json.load(file)

    enriched_routes = [_enrich_route_for_frontend(route) for route in routes]

    valid_routes = [
        route
        for route in enriched_routes
        if route.get("courier_id")
        and route.get("predicted_sequence")
        and route.get("stops")
    ]

    skipped = len(enriched_routes) - len(valid_routes)

    try:
        conn.execute_write(PERSIST_ASSIGNED_ROUTE_QUERY, {"routes": valid_routes})
        print(f"Loaded {len(valid_routes)} assigned routes into Aura.")
        if skipped:
            print(f"Skipped {skipped} invalid assigned routes.")
    finally:
        conn.close()


# ============================================================
# Main seed function
# ============================================================

def seed_aura_logistics():
    load_cities_to_aura()
    load_hubs_to_aura()
    load_hub_distances_to_aura()

    load_synthetic_couriers_to_aura(PIPELINE_DATA_DIR / "synthetic_couriers.json")
    load_synthetic_orders_to_aura(PIPELINE_DATA_DIR / "synthetic_orders.json")

    assigned_routes = PIPELINE_OUTPUT_DIR / "assigned_routes.json"

    if assigned_routes.is_file():
        load_assigned_routes_to_aura(assigned_routes)
    else:
        print(f"Skipping assigned routes — not found at {assigned_routes}")

    from aura_graphdb.aura_profiles import sync_all_profiles_from_supabase

    try:
        synced = sync_all_profiles_from_supabase()
        print(f"Synced {synced} Supabase profiles into Aura.")
    except Exception as exc:
        print(f"Profile sync skipped/failed: {exc}")

    print("Aura logistics seed completed.")


if __name__ == "__main__":
    seed_aura_logistics()