-- Count all nodes
MATCH (n)
RETURN labels(n) AS label, count(n) AS count;

-- Find hubs by city
MATCH (h:Hub)-[:LOCATED_IN]->(c:City)
RETURN c.city_name, h.hub_id, h.name, h.is_warehouse, h.is_delivery_hub, h.is_mixed_hub
ORDER BY c.city_name, h.hub_id;

-- Top hub routes by distance
MATCH (h1:Hub)-[r:ROUTE_TO]->(h2:Hub)
RETURN h1.hub_id AS from_hub, h2.hub_id AS to_hub, r.avg_distance_km AS distance
ORDER BY distance DESC
LIMIT 10;

-- Most active grid routes
MATCH (g:GridRoute)
RETURN g.from_grid_x, g.from_grid_y, g.to_grid_x, g.to_grid_y, g.num_trips
ORDER BY g.num_trips DESC
LIMIT 10;

-- Couriers with most loaded segments
MATCH (c:Courier)-[:TRAVELLED_SEGMENT]->(s:CourierSegment)
RETURN c.courier_id, count(s) AS segment_count
ORDER BY segment_count DESC
LIMIT 10;

-- Pickup and delivery orders assigned to a courier
MATCH (c:Courier {courier_id: $courier_id})
OPTIONAL MATCH (p:PickupOrder)-[:ASSIGNED_TO]->(c)
OPTIONAL MATCH (d:DeliveryOrder)-[:ASSIGNED_TO]->(c)
RETURN c.courier_id,
       count(DISTINCT p) AS pickup_orders,
       count(DISTINCT d) AS delivery_orders;