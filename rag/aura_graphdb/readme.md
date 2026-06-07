Here is the clean backend flow summary.

1. Admin creates a courier

Frontend form takes:

name
email
password
city_name
hub_name

Example:

{
  "name": "Courier One",
  "email": "courier1@example.com",
  "password": "test123",
  "city_name": "Chongqing",
  "hub_name": "Hub_1"
}

Backend route should call:

from aura_graphdb.aura_courier import create_courier_user

Function called:

create_courier_user(
    name=name,
    email=email,
    password=password,
    city_name=city_name,
    hub_name=hub_name,
    ds=318
)

What happens inside backend:

1. Check if courier email already exists in AuraDB.
2. Generate unique courier_id using uuid.uuid4().hex.
3. Hash password.
4. Find selected Hub by hub_name.
5. Find selected City by city_name.
6. Take start_lat_wgs84 from hub.latitude.
7. Take start_lon_wgs84 from hub.longitude.
8. Create Courier node.
9. Create/MATCH Role node for courier.
10. Connect Courier to Role, City, and Hub.

Nodes created/used:

(:Courier)
(:Role {role_id: 2, role_name: "courier"})
(:City)
(:Hub)

Relationships created:

(:Courier)-[:HAS_ROLE]->(:Role)
(:Courier)-[:OPERATES_IN]->(:City)
(:Courier)-[:ASSIGNED_TO_HUB]->(:Hub)

Courier node stores:

{
  "courier_id": "3d422549d258c991f749937347d42abe",
  "name": "Courier One",
  "email": "courier1@example.com",
  "city_name": "Chongqing",
  "hub_name": "Hub_1",
  "ds": 318,
  "start_lat_wgs84": 30.027772,
  "start_lon_wgs84": 101.702724
}

The courier_id is generated automatically, not entered by admin.

2. Logistics manager creates a new order

Frontend form takes only:

from_hub_name
to_hub_name
delivery_date
ds
receipt_time
notes optional

Example:

{
  "from_hub_name": "Hub_1",
  "to_hub_name": "Hub_5",
  "delivery_date": "2026-06-03",
  "ds": 318,
  "receipt_time": "08:00:00",
  "notes": "priority order"
}

Backend combines:

delivery_date + receipt_time

into:

2026-06-03 08:00:00

Backend route should call:

from aura_graphdb.aura_order import create_order_and_assign_nearest_courier

Function called:

create_order_and_assign_nearest_courier(
    from_hub_name=from_hub_name,
    to_hub_name=to_hub_name,
    delivery_day=delivery_date,
    receipt_time=f"{delivery_date} {receipt_time}",
    ds=ds,
    extra_notes=notes
)

What happens inside backend:

1. Generate unique order_id using uuid.
2. Find from_hub by from_hub_name.
3. Find to_hub by to_hub_name.
4. Ensure both hubs are in the same city.
5. Get order pickup/receipt coordinates from from_hub:
   receipt_lat_wgs84 = from_hub.latitude
   receipt_lon_wgs84 = from_hub.longitude
6. Get order destination coordinates from to_hub:
   lat_wgs84 = to_hub.latitude
   lon_wgs84 = to_hub.longitude
7. Get aoi_id and typecode from to_hub.
8. Find active couriers in the same city.
9. Calculate distance between each courier start location and from_hub.
10. Pick nearest courier.
11. Create Order node.
12. Store assigned_courier_id directly on Order.
13. Create Notes node.
14. Connect Order to from hub, to hub, courier, and notes.

Nodes created/used:

(:Order)
(:Notes)
(:Courier)
(:Hub)
(:City)

Relationships created:

(:Order)-[:FROM_HUB]->(:Hub)
(:Order)-[:TO_HUB]->(:Hub)
(:Order)-[:ASSIGNED_TO]->(:Courier)
(:Order)-[:HAS_NOTES]->(:Notes)

Order node stores:

{
  "order_id": "ord-a82f1c93d204",
  "lat_wgs84": 30.006372,
  "lon_wgs84": 101.768135,
  "city_name": "Chongqing",
  "ds": 318,
  "delivery_day": "2026-06-03",
  "receipt_time": "2026-06-03 08:00:00",
  "typecode": "from to_hub.typecode",
  "aoi_id": "from to_hub.aoi_id",
  "receipt_lat_wgs84": 30.027772,
  "receipt_lon_wgs84": 101.702724,
  "from_hub_name": "Hub_1",
  "to_hub_name": "Hub_5",
  "assigned_courier_id": "nearest courier id",
  "assigned_courier_name": "nearest courier name",
  "nearest_courier_distance_m": 842.7
}

Notes node stores:

{
  "notes_id": "note-xxxx",
  "text": "priority order",
  "cluster": "to_hub_id",
  "courier_id": "assigned courier id"
}
3. Seeding hubs and cities before these features

Before admin creates couriers or logistics manager creates orders, AuraDB must already have cities and hubs.

Function called:

from aura_graphdb.aura_seed_logistics import seed_aura_logistics

Run once:

python -m aura_graphdb.aura_seed_logistics

This loads from Supabase:

cities
hubs

into AuraDB.

Creates:

(:City)
(:Hub)-[:LOCATED_IN]->(:City)

This is required because courier creation and order creation both depend on existing Hub and City nodes.

### Profile auth (Supabase → Aura sync)

User accounts are stored in **Supabase** (`profiles`, `user_roles`, `roles`). After registration, profiles are mirrored into Aura:

```python
from aura_graphdb.supabase_auth import register_user_in_supabase
from aura_graphdb.aura_profiles import sync_profile_to_aura

supabase_result = register_user_in_supabase(...)
if supabase_result["success"]:
    user = supabase_result["user"]
    sync_profile_to_aura(
        profile_id=user["id"],
        name=user["name"],
        email=user["email"],
        role_id=user["role_id"],
        role_name=user["role"],
    )
```

`register_user_with_password()` in `aura_auth.py` performs this automatically.

**Reseed Aura (clear + logistics + profile sync):**

```bash
cd rag
python -m aura_graphdb.aura_reseed
```

Final simple flow
Supabase cities/hubs
        ↓
aura_seed_logistics.py
        ↓
AuraDB has City + Hub nodes


Admin creates courier
        ↓
backend route
        ↓
create_courier_user()
        ↓
AuraDB creates Courier node and assigns it to City + Hub


Logistics manager creates order
        ↓
backend route
        ↓
create_order_and_assign_nearest_courier()
        ↓
AuraDB creates Order node, finds nearest Courier, stores assigned_courier_id

So yes: the generated order_id is connected to the nearest courier using:

(:Order)-[:ASSIGNED_TO]->(:Courier)

and the nearest courier ID is also stored as:

Order.assigned_courier_id