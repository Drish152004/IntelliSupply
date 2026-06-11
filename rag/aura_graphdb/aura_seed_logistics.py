import json
import pandas as pd
from pathlib import Path

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

def load_cities_to_aura():
    engine = get_supabase_engine()
    conn = AuraConnection()

    df = pd.read_sql(
        """
        SELECT city_id, city_name
        FROM cities
        ORDER BY city_id
        """,
        engine
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

def load_hubs_to_aura():
    """Load hubs from Supabase directly into Aura using lat/lng — no coordinate conversion."""
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
        print(f"Loaded {len(rows)} hubs into Aura (lat/lng direct from Supabase, no conversion).")
    finally:
        conn.close()


def load_hub_distances_to_aura():
    """Load hub_distances from Supabase as (:Hub)-[:CONNECTED_TO]->(:Hub) relationships."""
    engine = get_supabase_engine()
    conn = AuraConnection()

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
        print(f"Loaded {len(rows)} hub distance relationships into Aura (CONNECTED_TO).")
    finally:
        conn.close()

def load_synthetic_couriers_to_aura(json_path="synthetic_couriers.json"):
    conn = AuraConnection()

    with open(json_path, "r", encoding="utf-8") as file:
        rows = json.load(file)

    query = """
    UNWIND $rows AS row

    MATCH (city:City {city_name: row.city_name})

    OPTIONAL MATCH (namedHub:Hub {name: row.hub_name})-[:LOCATED_IN]->(city)
    WITH row, city, namedHub
    CALL (row, city, namedHub) {
        MATCH (city)<-[:LOCATED_IN]-(anyHub:Hub)
        WITH namedHub, anyHub
        ORDER BY anyHub.hub_id
        RETURN collect(anyHub)[0] AS fallbackHub
    }
    WITH row, city, coalesce(namedHub, fallbackHub) AS hub

    MERGE (role:Role {role_id: 2})
    SET role.role_name = "courier"

    MERGE (courier:Courier {courier_id: row.courier_id})
    ON CREATE SET courier.created_at = datetime()
    SET
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
        print(f"Loaded {len(rows)} synthetic couriers into Aura (coords from hub.lat/hub.lng).")
    finally:
        conn.close()

def load_synthetic_orders_to_aura(json_path="synthetic_orders.json"):
    conn = AuraConnection()

    with open(json_path, "r", encoding="utf-8") as file:
        rows = json.load(file)

    query = """
    UNWIND $rows AS row

    MERGE (city:City {city_name: row.city_name})

    MERGE (order:Order {order_id: row.order_id})
    ON CREATE SET order.created_at = datetime()
    SET
        order.lat_wgs84 = toFloat(row.lat_wgs84),
        order.lon_wgs84 = toFloat(row.lon_wgs84),
        order.city_name = row.city_name,
        order.ds = toInteger(row.ds),
        order.delivery_day = row.delivery_day,
        order.receipt_time = row.receipt_time,
        order.typecode = row.typecode,
        order.aoi_id = row.aoi_id,
        order.receipt_lat_wgs84 = toFloat(row.receipt_lat_wgs84),
        order.receipt_lon_wgs84 = toFloat(row.receipt_lon_wgs84),
        order.from_hub_name = row.from_hub_name,
        order.to_hub_name = row.to_hub_name,
        order.notes_text = row.notes,
        order.updated_at = datetime()

    MERGE (notes:Notes {notes_id: "note_" + row.order_id})
    ON CREATE SET notes.created_at = datetime()
    SET
        notes.text = coalesce(row.notes, ""),
        notes.updated_at = datetime()

    MERGE (order)-[:BELONGS_TO_CITY]->(city)
    MERGE (order)-[:HAS_NOTES]->(notes)

    WITH order, city, row
    OPTIONAL MATCH (fromHub:Hub {name: row.from_hub_name})-[:LOCATED_IN]->(city)
    OPTIONAL MATCH (toHub:Hub {name: row.to_hub_name})-[:LOCATED_IN]->(city)
    FOREACH (_ IN CASE WHEN fromHub IS NOT NULL THEN [1] ELSE [] END |
        MERGE (order)-[:FROM_HUB]->(fromHub)
    )
    FOREACH (_ IN CASE WHEN toHub IS NOT NULL THEN [1] ELSE [] END |
        MERGE (order)-[:TO_HUB]->(toHub)
    )
    """

    try:
        conn.execute_write(query, {"rows": rows})
        print(f"Loaded {len(rows)} synthetic orders into Aura.")
    finally:
        conn.close()

def load_assigned_routes_to_aura(json_path=None):
    conn = AuraConnection()

    if json_path is None:
        json_path = PIPELINE_OUTPUT_DIR / "assigned_routes.json"
    json_path = Path(json_path)

    with open(json_path, "r", encoding="utf-8") as file:
        routes = json.load(file)

    for route in routes:
        if not route.get("route_prediction_id"):
            delivery_day = route.get("delivery_day", "unknown")
            route["route_prediction_id"] = f"{route['courier_id']}_{delivery_day}"
        route.pop("cluster_id", None)

    try:
        conn.execute_write(PERSIST_ASSIGNED_ROUTE_QUERY, {"routes": routes})
        print(f"Loaded {len(routes)} assigned routes into Aura.")
    finally:
        conn.close()

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