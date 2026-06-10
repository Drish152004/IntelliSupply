"""Shared Cypher for persisting ML route predictions to Aura."""

PERSIST_ASSIGNED_ROUTE_QUERY = """
UNWIND $routes AS route

MATCH (courier:Courier {courier_id: route.courier_id})

OPTIONAL MATCH (courier)-[:OPERATES_IN]->(existing_city:City)

WITH route, courier, existing_city

MERGE (rp:RoutePrediction {route_prediction_id: route.route_prediction_id})
ON CREATE SET
    rp.created_at = datetime()
SET
    rp.courier_id = route.courier_id,
    rp.order_ids = route.order_ids,
    rp.predicted_sequence = route.predicted_sequence,
    rp.predicted_stops_json = route.predicted_stops_json,
    rp.predicted_eta_min = CASE
        WHEN route.predicted_eta_min IS NULL THEN NULL
        ELSE toFloat(route.predicted_eta_min)
    END,
    rp.ds = toInteger(route.ds),
    rp.delivery_day = route.delivery_day,
    rp.city_name = coalesce(route.city_name, existing_city.city_name),
    rp.cluster_id = CASE
        WHEN route.cluster_id IS NULL THEN NULL
        ELSE toInteger(route.cluster_id)
    END,
    rp.stop_count = size(route.stops),
    rp.updated_at = datetime()

MERGE (rp)-[:FOR_COURIER]->(courier)

WITH route, courier, rp, existing_city

FOREACH (_ IN CASE WHEN existing_city IS NULL THEN [] ELSE [1] END |
    MERGE (rp)-[:BELONGS_TO_CITY]->(existing_city)
)

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
    rel.lat_wgs84 = CASE
        WHEN stop.lat_wgs84 IS NULL THEN NULL
        ELSE toFloat(stop.lat_wgs84)
    END,
    rel.lon_wgs84 = CASE
        WHEN stop.lon_wgs84 IS NULL THEN NULL
        ELSE toFloat(stop.lon_wgs84)
    END
"""