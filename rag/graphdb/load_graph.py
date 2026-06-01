import pandas as pd

from graphdb.neo4j_connection import Neo4jConnection
from graphdb.supabase_connection import get_supabase_engine


BATCH_SIZE = 10_000


# =========================================================
# GENERIC BATCH HELPERS
# =========================================================

def read_table_batch(engine, table_name, limit=10_000, offset=0, order_by=None):
    """
    Reads one batch from a Supabase/Postgres table.
    """
    order_clause = f"ORDER BY {order_by}" if order_by else ""

    query = f"""
        SELECT *
        FROM {table_name}
        {order_clause}
        LIMIT {limit}
        OFFSET {offset};
    """

    df = pd.read_sql(query, engine)
    df = df.where(pd.notnull(df), None)

    return df.to_dict("records")


def load_table_in_batches(
    engine,
    conn,
    table_name,
    cypher_query,
    order_by=None,
    batch_size=10_000,
    label=None
):
    """
    Generic batch loader:
    1. Reads table from Supabase/Postgres in chunks.
    2. Sends each chunk to Neo4j.
    3. Repeats until no rows are left.
    """
    offset = 0
    total_loaded = 0

    while True:
        rows = read_table_batch(
            engine=engine,
            table_name=table_name,
            limit=batch_size,
            offset=offset,
            order_by=order_by
        )

        if not rows:
            break

        conn.execute_write(cypher_query, {"rows": rows})

        total_loaded += len(rows)
        offset += batch_size

        print(f"Loaded {total_loaded} rows from {label or table_name}")

    print(f"Finished loading {label or table_name}. Total rows: {total_loaded}")


# =========================================================
# LOAD CITIES
# =========================================================

def load_cities(conn, engine):
    query = """
    UNWIND $rows AS row
    MERGE (c:City {city_id: toInteger(row.city_id)})
    SET c.city_name = row.city_name
    """

    load_table_in_batches(
        engine=engine,
        conn=conn,
        table_name="cities",
        cypher_query=query,
        order_by="city_id",
        batch_size=BATCH_SIZE,
        label="cities"
    )


# =========================================================
# LOAD COURIERS
# =========================================================

def load_couriers(conn, engine):
    query = """
    UNWIND $rows AS row
    MERGE (cr:Courier {courier_id: row.courier_id})
    SET cr.status = row.status

    WITH cr, row
    OPTIONAL MATCH (city:City {city_id: toInteger(row.city_id)})
    FOREACH (_ IN CASE WHEN city IS NULL THEN [] ELSE [1] END |
        MERGE (cr)-[:OPERATES_IN]->(city)
    )
    """

    load_table_in_batches(
        engine=engine,
        conn=conn,
        table_name="couriers",
        cypher_query=query,
        order_by="courier_id",
        batch_size=BATCH_SIZE,
        label="couriers"
    )


# =========================================================
# LOAD HUBS
# =========================================================

def load_hubs(conn, engine):
    query = """
    UNWIND $rows AS row
    MERGE (h:Hub {hub_id: toInteger(row.hub_id)})
    SET
        h.name = row.name,
        h.poi_lat = toFloat(row.poi_lat),
        h.poi_lng = toFloat(row.poi_lng),
        h.latitude = toFloat(row.latitude),
        h.longitude = toFloat(row.longitude),
        h.aoi_id = row.aoi_id,
        h.typecode = row.typecode,
        h.rep_dipan_id = row.rep_dipan_id,
        h.is_warehouse = row.is_warehouse,
        h.is_delivery_hub = row.is_delivery_hub,
        h.is_mixed_hub = row.is_mixed_hub,
        h.capacity = row.capacity

    WITH h, row
    OPTIONAL MATCH (city:City {city_id: toInteger(row.city_id)})
    FOREACH (_ IN CASE WHEN city IS NULL THEN [] ELSE [1] END |
        MERGE (h)-[:LOCATED_IN]->(city)
    )
    """

    load_table_in_batches(
        engine=engine,
        conn=conn,
        table_name="hubs",
        cypher_query=query,
        order_by="hub_id",
        batch_size=BATCH_SIZE,
        label="hubs"
    )


# =========================================================
# LOAD HUB METRICS
# =========================================================

def load_hub_metrics(conn, engine):
    query = """
    UNWIND $rows AS row
    MATCH (h:Hub {hub_id: toInteger(row.hub_id)})
    MERGE (m:HubMetrics {hub_id: toInteger(row.hub_id)})
    SET
        m.pickup_count = toInteger(row.pickup_count),
        m.delivery_count = toInteger(row.delivery_count),
        m.total = toInteger(row.total),
        m.pickup_ratio = toFloat(row.pickup_ratio),
        m.delivery_ratio = toFloat(row.delivery_ratio)

    MERGE (h)-[:HAS_METRICS]->(m)
    """

    load_table_in_batches(
        engine=engine,
        conn=conn,
        table_name="hub_metrics",
        cypher_query=query,
        order_by="hub_id",
        batch_size=BATCH_SIZE,
        label="hub_metrics"
    )


# =========================================================
# LOAD HUB ROUTES
# =========================================================

def load_hub_routes(conn, engine):
    query = """
    UNWIND $rows AS row
    MATCH (fromHub:Hub {hub_id: toInteger(row.from_hub_id)})
    MATCH (toHub:Hub {hub_id: toInteger(row.to_hub_id)})
    MERGE (fromHub)-[r:ROUTE_TO]->(toHub)
    SET
        r.route_id = toInteger(row.route_id),
        r.avg_time_min = row.avg_time_min,
        r.avg_distance_km = row.avg_distance_km,
        r.num_trips = row.num_trips
    """

    load_table_in_batches(
        engine=engine,
        conn=conn,
        table_name="hub_routes",
        cypher_query=query,
        order_by="route_id",
        batch_size=BATCH_SIZE,
        label="hub_routes"
    )


# =========================================================
# LOAD GRID ROUTES
# =========================================================

def load_grid_routes(conn, engine):
    query = """
    UNWIND $rows AS row
    MERGE (g:GridRoute {grid_route_id: toInteger(row.grid_route_id)})
    SET
        g.from_grid_x = toInteger(row.from_grid_x),
        g.from_grid_y = toInteger(row.from_grid_y),
        g.to_grid_x = toInteger(row.to_grid_x),
        g.to_grid_y = toInteger(row.to_grid_y),
        g.avg_time_sec = toFloat(row.avg_time_sec),
        g.avg_distance_km = toFloat(row.avg_distance_km),
        g.avg_speed_kmph = toFloat(row.avg_speed_kmph),
        g.num_trips = toInteger(row.num_trips)
    """

    load_table_in_batches(
        engine=engine,
        conn=conn,
        table_name="grid_routes",
        cypher_query=query,
        order_by="grid_route_id",
        batch_size=BATCH_SIZE,
        label="grid_routes"
    )


# =========================================================
# LOAD PICKUP ORDERS
# =========================================================

def load_pickup_orders(conn, engine):
    query = """
    UNWIND $rows AS row
    MERGE (p:PickupOrder {pickup_id: row.pickup_id})
    SET
        p.from_dipan_id = row.from_dipan_id,
        p.accept_time = row.accept_time,
        p.book_start_time = row.book_start_time,
        p.expect_got_time = row.expect_got_time,
        p.poi_lng = toFloat(row.poi_lng),
        p.poi_lat = toFloat(row.poi_lat),
        p.aoi_id = row.aoi_id,
        p.typecode = row.typecode,
        p.got_time = row.got_time,
        p.got_gps_time = row.got_gps_time,
        p.got_gps_lng = toFloat(row.got_gps_lng),
        p.got_gps_lat = toFloat(row.got_gps_lat),
        p.ds = toInteger(row.ds)

    WITH p, row
    OPTIONAL MATCH (cr:Courier {courier_id: row.courier_id})
    FOREACH (_ IN CASE WHEN cr IS NULL THEN [] ELSE [1] END |
        MERGE (p)-[:ASSIGNED_TO]->(cr)
    )

    WITH p, row
    OPTIONAL MATCH (city:City {city_id: toInteger(row.city_id)})
    FOREACH (_ IN CASE WHEN city IS NULL THEN [] ELSE [1] END |
        MERGE (p)-[:BELONGS_TO_CITY]->(city)
    )
    """

    load_table_in_batches(
        engine=engine,
        conn=conn,
        table_name="pickup_orders",
        cypher_query=query,
        order_by="pickup_id",
        batch_size=BATCH_SIZE,
        label="pickup_orders"
    )


# =========================================================
# LOAD DELIVERY ORDERS
# =========================================================

def load_delivery_orders(conn, engine):
    query = """
    UNWIND $rows AS row
    MERGE (d:DeliveryOrder {delivery_id: row.delivery_id})
    SET
        d.from_dipan_id = row.from_dipan_id,
        d.poi_lng = toFloat(row.poi_lng),
        d.poi_lat = toFloat(row.poi_lat),
        d.aoi_id = row.aoi_id,
        d.typecode = row.typecode,
        d.receipt_time = row.receipt_time,
        d.receipt_lng = toFloat(row.receipt_lng),
        d.receipt_lat = toFloat(row.receipt_lat),
        d.sign_time = row.sign_time,
        d.ds = toInteger(row.ds)

    WITH d, row
    OPTIONAL MATCH (cr:Courier {courier_id: row.courier_id})
    FOREACH (_ IN CASE WHEN cr IS NULL THEN [] ELSE [1] END |
        MERGE (d)-[:ASSIGNED_TO]->(cr)
    )

    WITH d, row
    OPTIONAL MATCH (city:City {city_id: toInteger(row.city_id)})
    FOREACH (_ IN CASE WHEN city IS NULL THEN [] ELSE [1] END |
        MERGE (d)-[:BELONGS_TO_CITY]->(city)
    )
    """

    load_table_in_batches(
        engine=engine,
        conn=conn,
        table_name="delivery_orders",
        cypher_query=query,
        order_by="delivery_id",
        batch_size=BATCH_SIZE,
        label="delivery_orders"
    )


# =========================================================
# LOAD COURIER SEGMENTS
# =========================================================

def load_courier_segments(conn, engine):
    query = """
    UNWIND $rows AS row
    MERGE (s:CourierSegment {segment_id: toInteger(row.segment_id)})
    SET
        s.prev_lat = toFloat(row.prev_lat),
        s.prev_lng = toFloat(row.prev_lng),
        s.lat = toFloat(row.lat),
        s.lng = toFloat(row.lng),
        s.distance_m = toFloat(row.distance_m),
        s.distance_km = toFloat(row.distance_km),
        s.time_sec = toFloat(row.time_sec),
        s.time_hr = toFloat(row.time_hr),
        s.speed_kmph = toFloat(row.speed_kmph)

    WITH s, row
    OPTIONAL MATCH (cr:Courier {courier_id: row.courier_id})
    FOREACH (_ IN CASE WHEN cr IS NULL THEN [] ELSE [1] END |
        MERGE (cr)-[:TRAVELLED_SEGMENT]->(s)
    )

    WITH s, row
    OPTIONAL MATCH (g:GridRoute {grid_route_id: toInteger(row.grid_route_id)})
    FOREACH (_ IN CASE WHEN g IS NULL THEN [] ELSE [1] END |
        MERGE (s)-[:USED_GRID_ROUTE]->(g)
    )
    """

    load_table_in_batches(
        engine=engine,
        conn=conn,
        table_name="courier_segments",
        cypher_query=query,
        order_by="segment_id",
        batch_size=BATCH_SIZE,
        label="courier_segments"
    )


# =========================================================
# MAIN LOAD FUNCTION
# =========================================================

def load_all():
    engine = get_supabase_engine()
    conn = Neo4jConnection()

    try:
        load_cities(conn, engine)
        load_couriers(conn, engine)
        load_hubs(conn, engine)
        load_hub_metrics(conn, engine)
        load_hub_routes(conn, engine)
        load_grid_routes(conn, engine)
        load_pickup_orders(conn, engine)
        #load_delivery_orders(conn, engine)
        #load_courier_segments(conn, engine)

        print("Loaded graph from Supabase successfully.")

    finally:
        conn.close()


if __name__ == "__main__":
    load_all()