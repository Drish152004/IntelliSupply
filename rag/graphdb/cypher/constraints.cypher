CREATE CONSTRAINT city_id_unique IF NOT EXISTS
FOR (c:City)
REQUIRE c.city_id IS UNIQUE;

CREATE CONSTRAINT courier_id_unique IF NOT EXISTS
FOR (c:Courier)
REQUIRE c.courier_id IS UNIQUE;

CREATE CONSTRAINT hub_id_unique IF NOT EXISTS
FOR (h:Hub)
REQUIRE h.hub_id IS UNIQUE;

CREATE CONSTRAINT pickup_id_unique IF NOT EXISTS
FOR (p:PickupOrder)
REQUIRE p.pickup_id IS UNIQUE;

CREATE CONSTRAINT delivery_id_unique IF NOT EXISTS
FOR (d:DeliveryOrder)
REQUIRE d.delivery_id IS UNIQUE;

CREATE CONSTRAINT grid_route_id_unique IF NOT EXISTS
FOR (g:GridRoute)
REQUIRE g.grid_route_id IS UNIQUE;

CREATE CONSTRAINT segment_id_unique IF NOT EXISTS
FOR (s:CourierSegment)
REQUIRE s.segment_id IS UNIQUE;

CREATE INDEX city_name_index IF NOT EXISTS
FOR (c:City)
ON (c.city_name);

CREATE INDEX hub_type_index IF NOT EXISTS
FOR (h:Hub)
ON (h.is_warehouse, h.is_delivery_hub, h.is_mixed_hub);

CREATE INDEX grid_route_lookup_index IF NOT EXISTS
FOR (g:GridRoute)
ON (g.from_grid_x, g.from_grid_y, g.to_grid_x, g.to_grid_y);