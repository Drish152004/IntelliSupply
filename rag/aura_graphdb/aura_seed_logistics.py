import json
import pandas as pd

from aura_graphdb.aura_connection import AuraConnection
from aura_graphdb.supabase_connection import get_supabase_engine


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
    ON CREATE SET
        hub.created_at = datetime()

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

    MERGE (city:City {city_name: row.city_name})

    MERGE (role:Role {role_id: 2})
    SET role.role_name = "courier"

    MERGE (courier:Courier {courier_id: row.courier_id})
    SET
        courier.city_name = row.city_name,
        courier.ds = toInteger(row.ds),
        courier.start_lat_wgs84 = toFloat(row.start_lat_wgs84),
        courier.start_lon_wgs84 = toFloat(row.start_lon_wgs84),
        courier.is_active = true,
        courier.updated_at = datetime()
    ON CREATE SET
        courier.created_at = datetime()

    MERGE (courier)-[:HAS_ROLE]->(role)
    MERGE (courier)-[:OPERATES_IN]->(city)
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
    ON CREATE SET
        order.created_at = datetime()

    MERGE (notes:Notes {notes_id: "note_" + row.order_id})
    SET
        notes.text = row.notes,
        notes.updated_at = datetime()
    ON CREATE SET
        notes.created_at = datetime()

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

def load_assigned_routes_to_aura(json_path="assigned_routes.json"):
    conn = AuraConnection()

    with open(json_path, "r", encoding="utf-8") as file:
        routes = json.load(file)

    query = """
    UNWIND $routes AS route

    MATCH (courier:Courier {courier_id: route.courier_id})
    MERGE (city:City {city_name: route.city_name})

    MERGE (rp:RoutePrediction {
        route_prediction_id: route.courier_id + "_" + toString(route.ds) + "_" + route.delivery_day
    })
    SET
        rp.courier_id = route.courier_id,
        rp.cluster_id = toInteger(route.cluster_id),
        rp.city_name = route.city_name,
        rp.ds = toInteger(route.ds),
        rp.delivery_day = route.delivery_day,
        rp.order_ids = route.order_ids,
        rp.predicted_sequence = route.predicted_sequence,
        rp.stop_count = size(route.stops),
        rp.updated_at = datetime()
    ON CREATE SET
        rp.created_at = datetime()

    MERGE (rp)-[:FOR_COURIER]->(courier)
    MERGE (rp)-[:BELONGS_TO_CITY]->(city)

    WITH route, courier, rp
    UNWIND route.stops AS stop

    MATCH (order:Order {order_id: stop.order_id})

    SET
        order.assigned_courier_id = courier.courier_id,
        order.route_sequence = toInteger(stop.sequence),
        order.updated_at = datetime()

    MERGE (order)-[:ASSIGNED_TO]->(courier)

    MERGE (rp)-[rel:HAS_STOP]->(order)
    SET
        rel.sequence = toInteger(stop.sequence),
        rel.lat_wgs84 = toFloat(stop.lat_wgs84),
        rel.lon_wgs84 = toFloat(stop.lon_wgs84)
    """

    try:
        conn.execute_write(query, {"routes": routes})
        print(f"Loaded {len(routes)} assigned routes into Aura.")
    finally:
        conn.close()


# =========================================================
# MAIN SEED FUNCTION
# =========================================================

def seed_aura_logistics():
    load_cities_to_aura()
    load_hubs_to_aura()

    load_synthetic_couriers_to_aura("synthetic_data\synthetic_couriers.json")
    load_synthetic_orders_to_aura("synthetic_data\synthetic_orders.json")
    load_assigned_routes_to_aura("synthetic_data\assigned_routes.json")

    print("Aura logistics seed completed.")


if __name__ == "__main__":
    seed_aura_logistics()