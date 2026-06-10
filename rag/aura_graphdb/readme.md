## 1. Current Architecture

```text
User registers / logs in
        ↓
rag.supabase.supabase_auth.py handles authentication
        ↓
Supabase stores profile + role_id
        ↓
aura_profiles.py syncs profile + role into Aura
        ↓
Aura stores (:Profile)-[:HAS_ROLE]->(:Role)
```

```text
Admin creates courier
        ↓
Supabase creates user profile with courier role
        ↓
aura_profiles.py syncs Profile + Role into Aura
        ↓
aura_courier.py creates Courier node in Aura
        ↓
Courier is connected to City and Hub
```

```text
Logistics manager creates order
        ↓
aura_order.py creates Order node
        ↓
Nearest active courier is selected
        ↓
Order is connected to Courier, City, Hubs, and Notes
```

```text
ML route model runs
        ↓
aura_route_prediction.py stores predicted route result
        ↓
shared_cypher.py persists RoutePrediction + HAS_STOP relationships
        ↓
Dashboard / chatbot reads route data from Aura
```

---

## 2. Folder Structure

```text
aura_graphdb/
├── __init__.py
├── aura_connection.py
├── aura_constraints.py
├── aura_clear.py
├── aura_seed_logistics.py
├── aura_profiles.py
├── aura_courier.py
├── aura_order.py
├── aura_route_queries.py
├── aura_route_prediction.py
├── shared_cypher.py
├── aura_reseed.py
└── readme.md
```

---

## 3. What Each File Does

### `aura_connection.py`

Creates the Neo4j Aura connection and exposes helper methods to run Cypher queries.

Used by almost every Aura file.

Main responsibility:

```text
Connect to Aura
Run read queries
Run write queries
Close connection safely
```

---

### `aura_constraints.py`

Creates Neo4j constraints for important node IDs.

Example constraints:

```text
Profile.id unique
Profile.email unique
Role.role_id unique
Role.role_name unique
City.city_id unique
Hub.hub_id unique
Hub.name unique
Courier.courier_id unique
Courier.email unique
Order.order_id unique
Notes.notes_id unique
RoutePrediction.route_prediction_id unique
ETAPrediction.eta_prediction_id unique
```

Run:

```bash
python -m aura_graphdb.aura_constraints
```

This file does not delete nodes or relationships.

---

### `aura_clear.py`

Clears the graph database.

Usually contains logic similar to:

```cypher
MATCH (n)
DETACH DELETE n
```

Run only when you want to completely reset Aura.

```bash
python -m aura_graphdb.aura_clear
```

---

### `aura_seed_logistics.py`

Seeds initial logistics graph data into Aura.

It loads:

```text
cities
hubs
synthetic couriers
synthetic orders
assigned routes
Supabase profiles and roles
```

Data sources:

```text
Supabase/PostgreSQL → cities, hubs
ML pipeline data folder → synthetic_couriers.json, synthetic_orders.json
ML pipeline outputs folder → assigned_routes.json
Supabase profiles → synced through aura_profiles.py
```

Run:

```bash
python -m aura_graphdb.aura_seed_logistics
```

Important: cities and hubs must exist in Aura before courier creation and order creation can work.

---

### `aura_profiles.py`

Syncs Supabase profile records into Neo4j Aura.

Supabase is the source of truth for users and roles. Aura only stores graph mirror data.

Creates:

```text
(:Profile)-[:HAS_ROLE]->(:Role)
```

Profile stores:

```text
id
name
email
auth_provider
source
is_active
created_at
updated_at
```

Role stores:

```text
role_id
role_name
created_at
updated_at
```

Important functions:

```python
sync_profile_to_aura(...)
sync_all_profiles_from_supabase()
```

`sync_profile_to_aura()` is used after a new user registers.

`sync_all_profiles_from_supabase()` is used during reseeding or full sync.

---

### `aura_courier.py`

Creates and manages operational Courier nodes in Aura.

Authentication does not happen here. Login and password checking happen through Supabase auth.

This file creates:

```text
(:Courier)-[:HAS_ROLE]->(:Role)
(:Courier)-[:OPERATES_IN]->(:City)
(:Courier)-[:ASSIGNED_TO_HUB]->(:Hub)
(:Courier)-[:LINKED_TO_PROFILE]->(:Profile)
```

Main functions:

```python
get_courier_by_email(email)
create_courier_node(...)
deactivate_courier(courier_id)
```

Courier stores:

```text
courier_id
profile_id
name
email
city_id
city_name
hub_id
hub_name
ds
start_lat_wgs84
start_lon_wgs84
is_active
created_at
updated_at
```

The courier ID is generated automatically unless provided.

The courier start location is taken from the assigned hub:

```text
courier.start_lat_wgs84 = hub.latitude
courier.start_lon_wgs84 = hub.longitude
```

---

### `aura_order.py`

Creates a new order/shipment and assigns it to the nearest active courier.

Main function:

```python
create_order_and_assign_nearest_courier(...)
```

Inputs:

```text
from_hub_name
to_hub_name
delivery_day
receipt_time
ds
typecode optional
aoi_id optional
extra_notes optional
```

What it does:

```text
1. Generates order_id.
2. Finds source hub.
3. Finds destination hub.
4. Ensures both hubs are in the same city.
5. Gets pickup coordinates from source hub.
6. Gets delivery coordinates from destination hub.
7. Finds active couriers in the same city and ds.
8. Calculates distance from courier start location to source hub.
9. Picks the nearest courier.
10. Creates Order node.
11. Creates Notes node.
12. Connects Order to hubs, city, courier, and notes.
```

Creates:

```text
(:Order)-[:FROM_HUB]->(:Hub)
(:Order)-[:TO_HUB]->(:Hub)
(:Order)-[:BELONGS_TO_CITY]->(:City)
(:Order)-[:ASSIGNED_TO]->(:Courier)
(:Order)-[:HAS_NOTES]->(:Notes)
```

Current behavior:

```text
One courier can receive many orders.
There is no max-order limit per courier.
The nearest active courier is selected every time.
```

---

### `aura_route_queries.py`

Reads route, order, and courier assignment data from Aura.

This file is used by dashboards, chatbot, and ML input preparation.

Main functions:

```python
get_order_route(order_id)
get_recent_order_routes(limit=20)
get_orders_for_courier_day(courier_id, city_name, ds, delivery_day)
get_orders_for_courier(courier_id, limit=20)
answer_route_question(question)
```

Use cases:

```text
Show route for one order
Show recent created orders
Show orders assigned to one courier
Fetch courier-day orders for ML route prediction
Answer simple route-related chatbot questions
```

---

### `aura_route_prediction.py`

Stores ML route prediction results into Aura after the route model runs.

Main function:

```python
persist_ml_courier_route(...)
```

It stores:

```text
courier_id
order_ids
predicted_sequence
predicted_stops_json
predicted_eta_min
ds
delivery_day
city_name
cluster_id
stop_count
created_at
updated_at
```

Creates/updates:

```text
(:RoutePrediction)-[:FOR_COURIER]->(:Courier)
(:RoutePrediction)-[:BELONGS_TO_CITY]->(:City)
(:RoutePrediction)-[:HAS_STOP]->(:Order)
(:Order)-[:ASSIGNED_TO]->(:Courier)
```

This file should be called after the ML route model generates the predicted route.

---

### `shared_cypher.py`

Stores shared Cypher used for persisting ML route predictions.

Main object:

```python
PERSIST_ASSIGNED_ROUTE_QUERY
```

Used by:

```text
aura_seed_logistics.py
aura_route_prediction.py
```

This file keeps large Cypher separate so the Python files remain cleaner.

---

### `aura_reseed.py`

Convenience runner for reseeding Aura.

Typical flow:

```text
clear graph
create constraints
seed logistics data
sync profiles
```

Use carefully because it may clear all existing Aura graph data.

Example:

```bash
python -m aura_graphdb.aura_reseed
```

---

## 4. GraphDB Schema

### Profile Node

Represents a user profile mirrored from Supabase.

```text
(:Profile {
    id,
    name,
    email,
    auth_provider,
    source,
    is_active,
    created_at,
    updated_at
})
```

Example:

```text
Profile.id = Supabase profiles.id
Profile.source = "supabase"
```

Relationships:

```text
(:Profile)-[:HAS_ROLE]->(:Role)
(:Courier)-[:LINKED_TO_PROFILE]->(:Profile)
```

---

### Role Node

Represents user role.

```text
(:Role {
    role_id,
    role_name,
    created_at,
    updated_at
})
```

Current role mapping:

```text
1 → admin
2 → courier
3 → logistics_manager
4 → inventory_manager
```

Relationships:

```text
(:Profile)-[:HAS_ROLE]->(:Role)
(:Courier)-[:HAS_ROLE]->(:Role)
```

---

### City Node

Represents city-level geography.

```text
(:City {
    city_id,
    city_name
})
```

Relationships:

```text
(:Hub)-[:LOCATED_IN]->(:City)
(:Courier)-[:OPERATES_IN]->(:City)
(:Order)-[:BELONGS_TO_CITY]->(:City)
(:RoutePrediction)-[:BELONGS_TO_CITY]->(:City)
```

---

### Hub Node

Represents a logistics hub.

```text
(:Hub {
    hub_id,
    name,
    poi_lat,
    poi_lng,
    latitude,
    longitude,
    aoi_id,
    typecode,
    rep_dipan_id,
    city_id,
    city_name,
    is_warehouse,
    is_delivery_hub,
    is_mixed_hub,
    capacity,
    created_at,
    updated_at
})
```

Important coordinate meaning:

```text
poi_lat / poi_lng      → raw dataset coordinates
latitude / longitude   → usable WGS84 coordinates
```

Relationships:

```text
(:Hub)-[:LOCATED_IN]->(:City)
(:Courier)-[:ASSIGNED_TO_HUB]->(:Hub)
(:Order)-[:FROM_HUB]->(:Hub)
(:Order)-[:TO_HUB]->(:Hub)
```

---

### Courier Node

Represents operational courier data in Aura.

```text
(:Courier {
    courier_id,
    profile_id,
    name,
    email,
    city_id,
    city_name,
    hub_id,
    hub_name,
    ds,
    start_lat_wgs84,
    start_lon_wgs84,
    is_active,
    created_at,
    updated_at
})
```

Relationships:

```text
(:Courier)-[:HAS_ROLE]->(:Role)
(:Courier)-[:OPERATES_IN]->(:City)
(:Courier)-[:ASSIGNED_TO_HUB]->(:Hub)
(:Courier)-[:LINKED_TO_PROFILE]->(:Profile)
(:Order)-[:ASSIGNED_TO]->(:Courier)
(:RoutePrediction)-[:FOR_COURIER]->(:Courier)
```

---

### Order Node

Represents shipment/order data.

```text
(:Order {
    order_id,
    lat_wgs84,
    lon_wgs84,
    city_name,
    ds,
    delivery_day,
    receipt_time,
    typecode,
    aoi_id,
    receipt_lat_wgs84,
    receipt_lon_wgs84,
    from_hub_name,
    to_hub_name,
    assigned_courier_id,
    nearest_courier_distance_m,
    route_sequence,
    notes_text,
    created_at,
    updated_at
})
```

Coordinate meaning:

```text
receipt_lat_wgs84 / receipt_lon_wgs84 → pickup/source hub coordinates
lat_wgs84 / lon_wgs84                 → destination/to hub coordinates
```

Relationships:

```text
(:Order)-[:FROM_HUB]->(:Hub)
(:Order)-[:TO_HUB]->(:Hub)
(:Order)-[:BELONGS_TO_CITY]->(:City)
(:Order)-[:ASSIGNED_TO]->(:Courier)
(:Order)-[:HAS_NOTES]->(:Notes)
(:RoutePrediction)-[:HAS_STOP]->(:Order)
```

---

### Notes Node

Represents notes attached to an order.

```text
(:Notes {
    notes_id,
    text,
    cluster,
    courier_id,
    created_at,
    updated_at
})
```

Relationships:

```text
(:Order)-[:HAS_NOTES]->(:Notes)
```

---

### RoutePrediction Node

Represents ML route prediction output.

```text
(:RoutePrediction {
    route_prediction_id,
    courier_id,
    order_ids,
    predicted_sequence,
    predicted_stops_json,
    predicted_eta_min,
    ds,
    delivery_day,
    city_name,
    cluster_id,
    stop_count,
    created_at,
    updated_at
})
```

Relationships:

```text
(:RoutePrediction)-[:FOR_COURIER]->(:Courier)
(:RoutePrediction)-[:BELONGS_TO_CITY]->(:City)
(:RoutePrediction)-[:HAS_STOP]->(:Order)
```

`HAS_STOP` relationship properties:

```text
sequence
lat_wgs84
lon_wgs84
```

Example:

```text
(:RoutePrediction)-[:HAS_STOP {sequence: 1}]->(:Order)
(:RoutePrediction)-[:HAS_STOP {sequence: 2}]->(:Order)
(:RoutePrediction)-[:HAS_STOP {sequence: 3}]->(:Order)
```

---

### ETAPrediction Node

Planned or optional prediction node for ETA-specific output.

```text
(:ETAPrediction {
    eta_prediction_id,
    courier_id,
    order_id,
    predicted_eta,
    model_version,
    created_at
})
```

Possible relationships:

```text
(:ETAPrediction)-[:FOR_COURIER]->(:Courier)
(:ETAPrediction)-[:FOR_ORDER]->(:Order)
```

---

## 5. Main Workflows

### Workflow 1: Register/Login User

```text
User registers or logs in
        ↓
rag.supabase.supabase_auth.py handles authentication
        ↓
Supabase profiles, roles, user_roles are used
        ↓
aura_profiles.py syncs profile and role into Aura
        ↓
Aura stores Profile - HAS_ROLE -> Role
```

Supabase tables:

```text
profiles
roles
user_roles
```

Aura graph:

```text
(:Profile)-[:HAS_ROLE]->(:Role)
```

---

### Workflow 2: Admin Creates Courier

Frontend sends:

```json
{
  "name": "Courier One",
  "email": "courier1@example.com",
  "password": "test123",
  "city_name": "Chongqing",
  "hub_name": "Hub_1"
}
```

Backend flow:

```text
1. register_user_in_supabase() creates user in Supabase.
2. sync_profile_to_aura() mirrors Profile and Role into Aura.
3. create_courier_node() creates Courier operational node in Aura.
4. Courier is connected to Role, City, Hub, and Profile.
```

Aura graph created:

```text
(:Courier)-[:HAS_ROLE]->(:Role)
(:Courier)-[:OPERATES_IN]->(:City)
(:Courier)-[:ASSIGNED_TO_HUB]->(:Hub)
(:Courier)-[:LINKED_TO_PROFILE]->(:Profile)
```

---

### Workflow 3: Logistics Manager Creates Order

Frontend sends:

```json
{
  "from_hub_name": "Hub_1",
  "to_hub_name": "Hub_5",
  "delivery_date": "2026-06-03",
  "ds": 318,
  "receipt_time": "08:00:00",
  "notes": "priority order"
}
```

Backend combines:

```text
delivery_date + receipt_time
```

into:

```text
2026-06-03 08:00:00
```

Then calls:

```python
create_order_and_assign_nearest_courier(
    from_hub_name=from_hub_name,
    to_hub_name=to_hub_name,
    delivery_day=delivery_date,
    receipt_time=f"{delivery_date} {receipt_time}",
    ds=ds,
    extra_notes=notes,
)
```

Aura logic:

```text
1. Find from_hub.
2. Find to_hub.
3. Ensure both hubs belong to the same city.
4. Find active couriers in that city and ds.
5. Calculate courier distance to source hub.
6. Pick nearest courier.
7. Create Order node.
8. Create Notes node.
9. Connect Order to hubs, city, courier, and notes.
```

Aura graph created:

```text
(:Order)-[:FROM_HUB]->(:Hub)
(:Order)-[:TO_HUB]->(:Hub)
(:Order)-[:BELONGS_TO_CITY]->(:City)
(:Order)-[:ASSIGNED_TO]->(:Courier)
(:Order)-[:HAS_NOTES]->(:Notes)
```

---

### Workflow 4: ML Route Prediction Runs

After orders are assigned to a courier, ML route prediction can run.

Input can be fetched using:

```python
get_orders_for_courier_day(
    courier_id=courier_id,
    city_name=city_name,
    ds=ds,
    delivery_day=delivery_day,
)
```

After ML predicts route sequence and ETA, save result using:

```python
persist_ml_courier_route(
    courier_id=courier_id,
    order_ids=order_ids,
    predicted_sequence=predicted_sequence,
    stops=stops,
    predicted_eta_min=predicted_eta_min,
    ds=ds,
    city_name=city_name,
    delivery_day=delivery_day,
    cluster_id=cluster_id,
)
```

Aura graph created:

```text
(:RoutePrediction)-[:FOR_COURIER]->(:Courier)
(:RoutePrediction)-[:BELONGS_TO_CITY]->(:City)
(:RoutePrediction)-[:HAS_STOP {sequence}]->(:Order)
```

---

### Workflow 5: Dashboard or Chatbot Reads Route Data

Read one order route:

```python
get_order_route(order_id)
```

Read recent routes:

```python
get_recent_order_routes(limit=20)
```

Read courier orders:

```python
get_orders_for_courier(courier_id, limit=20)
```

Simple chatbot helper:

```python
answer_route_question(question)
```

Example question:

```text
show route for order ord-a82f1c93d204
```

---

## 6. Common Commands

### Create constraints

```bash
python -m aura_graphdb.aura_constraints
```

### Clear graph

```bash
python -m aura_graphdb.aura_clear
```

### Seed logistics graph

```bash
python -m aura_graphdb.aura_seed_logistics
```

### Reseed graph

```bash
python -m aura_graphdb.aura_reseed
```

### Sync all Supabase profiles into Aura

```bash
python -c "from aura_graphdb.aura_profiles import sync_all_profiles_from_supabase; print(sync_all_profiles_from_supabase())"
```

---

## 7. Useful Cypher Queries

### Count couriers

```cypher
MATCH (c:Courier)
RETURN count(DISTINCT c.courier_id) AS unique_courier_ids;
```

### Count orders

```cypher
MATCH (o:Order)
RETURN count(DISTINCT o.order_id) AS unique_order_ids;
```

### Count orders assigned to each courier

```cypher
MATCH (c:Courier)
OPTIONAL MATCH (o:Order)-[:ASSIGNED_TO]->(c)
RETURN
    c.courier_id AS courier_id,
    c.name AS courier_name,
    count(DISTINCT o.order_id) AS assigned_order_count
ORDER BY assigned_order_count DESC;
```

### See route for one order

```cypher
MATCH (o:Order {order_id: "ord-example"})
OPTIONAL MATCH (o)-[:FROM_HUB]->(fromHub:Hub)
OPTIONAL MATCH (o)-[:TO_HUB]->(toHub:Hub)
OPTIONAL MATCH (o)-[:ASSIGNED_TO]->(courier:Courier)
RETURN
    o.order_id AS order_id,
    fromHub.name AS from_hub,
    toHub.name AS to_hub,
    courier.courier_id AS courier_id,
    courier.name AS courier_name;
```

### See predicted stops for a route

```cypher
MATCH (rp:RoutePrediction)-[s:HAS_STOP]->(o:Order)
RETURN
    rp.route_prediction_id AS route_prediction_id,
    s.sequence AS stop_number,
    o.order_id AS order_id,
    s.lat_wgs84 AS lat,
    s.lon_wgs84 AS lon
ORDER BY route_prediction_id, stop_number;
```

---

## 8. Important Notes

* Supabase is the source of truth for authentication.
* Aura does not store passwords.
* `aura_profiles.py` only mirrors profile and role data into Aura.
* `aura_courier.py` only manages courier graph data.
* `aura_order.py` creates orders and assigns the nearest courier.
* One courier can receive more than two orders if that courier is nearest.
* Cities and hubs must be seeded before courier creation or order creation.
* Route prediction results are stored in `RoutePrediction` nodes after the ML model runs.
* Large route persistence Cypher is kept in `shared_cypher.py`.
