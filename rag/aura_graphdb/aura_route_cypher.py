"""Shared Cypher for persisting ML route predictions to Aura."""

PERSIST_ASSIGNED_ROUTE_QUERY = """
UNWIND $routes AS route

MATCH (courier:Courier {courier_id: route.courier_id})
MERGE (city:City {city_name: route.city_name})

MERGE (rp:RoutePrediction {
    route_prediction_id: route.courier_id + "_" + toString(route.ds) + "_" + route.delivery_day
})
ON CREATE SET rp.created_at = datetime()
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
