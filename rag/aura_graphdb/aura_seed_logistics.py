import json
import pandas as pd
from pathlib import Path

from aura_graphdb.aura_connection import AuraConnection
from aura_graphdb.supabase_connection import get_supabase_engine
from aura_graphdb.aura_route_cypher import PERSIST_ASSIGNED_ROUTE_QUERY

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


# =========================================================
# 1. LOAD CITIES FROM SUPABASE
# =========================================================

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


# =========================================================
# 2. LOAD HUBS FROM SUPABASE
# =========================================================

def load_hubs_to_aura():
    engine = get_supabase_engine()
    conn = AuraConnection()

    df = pd.read_sql(
        """
        SELECT
            h.hub_id,
            h.name,
            h.poi_lat,
            h.poi_lng,
            h.latitude,
            h.longitude,
            h.aoi_id,
            h.typecode,
            h.rep_dipan_id,
            h.city_id,
            h.is_warehouse,
            h.is_delivery_hub,
            h.is_mixed_hub,
            h.capacity,
            c.city_name
        FROM hubs h
        JOIN cities c
            ON h.city_id = c.city_id
        ORDER BY h.hub_id
        """,
        engine
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
        hub.name = row.name,
        hub.poi_lat = toFloat(row.poi_lat),
        hub.poi_lng = toFloat(row.poi_lng),
        hub.latitude = toFloat(row.latitude),
        hub.longitude = toFloat(row.longitude),
        hub.aoi_id = row.aoi_id,
        hub.typecode = row.typecode,
        hub.rep_dipan_id = row.rep_dipan_id,
        hub.city_id = toInteger(row.city_id),
        hub.city_name = row.city_name,
        hub.is_warehouse = row.is_warehouse,
        hub.is_delivery_hub = row.is_delivery_hub,
        hub.is_mixed_hub = row.is_mixed_hub,
        hub.capacity = row.capacity,
        hub.updated_at = datetime()

    MERGE (hub)-[:LOCATED_IN]->(city)
    """

    try:
        conn.execute_write(query, {"rows": rows})
        print(f"Loaded {len(rows)} hubs into Aura.")
    finally:
        conn.close()


# =========================================================
# 3. LOAD COURIERS FROM synthetic_couriers.json
# =========================================================

def load_synthetic_couriers_to_aura(json_path="synthetic_couriers.json"):
    conn = AuraConnection()

    with open(json_path, "r", encoding="utf-8") as file:
        rows = json.load(file)

    query = """
    UNWIND $rows AS row

    MATCH (city:City {city_name: row.city_name})<-[:LOCATED_IN]-(hub:Hub)
    WITH row, city, hub
    ORDER BY hub.hub_id
    WITH row, city, collect(hub)[0] AS hub

    MERGE (role:Role {role_id: 2})
    SET role.role_name = "courier"

    MERGE (courier:Courier {courier_id: row.courier_id})
    ON CREATE SET courier.created_at = datetime()
    SET
        courier.city_id = city.city_id,
        courier.city_name = row.city_name,
        courier.hub_id = hub.hub_id,
        courier.hub_name = hub.name,
        courier.ds = toInteger(row.ds),
        courier.start_lat_wgs84 = toFloat(row.start_lat_wgs84),
        courier.start_lon_wgs84 = toFloat(row.start_lon_wgs84),
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


# =========================================================
# 4. LOAD ORDERS FROM synthetic_orders.json
# =========================================================

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
        order.notes_text = row.notes,
        order.updated_at = datetime()

    MERGE (notes:Notes {notes_id: "note_" + row.order_id})
    ON CREATE SET notes.created_at = datetime()
    SET
        notes.text = row.notes,
        notes.updated_at = datetime()

    MERGE (order)-[:BELONGS_TO_CITY]->(city)
    MERGE (order)-[:HAS_NOTES]->(notes)
    """

    try:
        conn.execute_write(query, {"rows": rows})
        print(f"Loaded {len(rows)} synthetic orders into Aura.")
    finally:
        conn.close()


# =========================================================
# 5. LOAD ASSIGNED ROUTES FROM assigned_routes.json
# =========================================================

def load_assigned_routes_to_aura(json_path=None):
    conn = AuraConnection()

    if json_path is None:
        json_path = PIPELINE_OUTPUT_DIR / "assigned_routes.json"
    json_path = Path(json_path)

    with open(json_path, "r", encoding="utf-8") as file:
        routes = json.load(file)

    try:
        conn.execute_write(PERSIST_ASSIGNED_ROUTE_QUERY, {"routes": routes})
        print(f"Loaded {len(routes)} assigned routes into Aura.")
    finally:
        conn.close()


# =========================================================
# MAIN SEED FUNCTION
# =========================================================

def seed_aura_logistics():
    load_cities_to_aura()
    load_hubs_to_aura()

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