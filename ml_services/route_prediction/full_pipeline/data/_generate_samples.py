"""One-off generator for synthetic_orders.json and synthetic_couriers.json."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent
OUT = DATA_DIR.parents[1] / "notebooks" / "outputs"
df = pd.read_csv(OUT / "orders_clustered.csv")
ca = pd.read_csv(OUT / "cluster_assignments.csv")

DAY = "2026-06-03"
DS = 318
DAY2 = "2026-06-04"
DS2 = 319


def courier_start(courier_id: str, city: str, ds: int = DS) -> tuple[float, float]:
    rows = df[
        (df.delivery_user_id == courier_id) & (df.city_name == city) & (df.ds == ds)
    ].sort_values("receipt_time")
    if len(rows):
        row = rows.iloc[0]
        return float(row.lat_wgs84), float(row.lon_wgs84)
    row = ca[
        (ca.assigned_courier == courier_id) & (ca.city_name == city) & (ca.ds == ds)
    ].iloc[0]
    return float(row.centroid_lat), float(row.centroid_lon)


def resolve_courier(city: str, cluster_id: int, ds: int = DS) -> str:
    row = ca[(ca.city_name == city) & (ca.cluster_id == cluster_id) & (ca.ds == ds)]
    if row.empty:
        raise ValueError(f"No assignment for {city} cluster {cluster_id} ds={ds}")
    return str(row.iloc[0].assigned_courier)


def sample_cluster_orders(
    city: str,
    cluster_id: int,
    n: int,
    prefix: str,
    courier_id: str,
    *,
    ds: int = DS,
    delivery_day: str = DAY,
    hour_start: int = 8,
    seed: int = 0,
) -> list[dict]:
    pool = df[(df.city_name == city) & (df.cluster_id == cluster_id) & (df.ds == ds)]
    if pool.empty:
        raise ValueError(f"No orders for {city} cluster {cluster_id} ds={ds}")
    sub = pool.sample(n=min(n, len(pool)), random_state=seed)
    if len(sub) < n:
        sub = pool.head(n)
    rlat, rlon = courier_start(courier_id, city, min(ds, DS))
    orders = []
    for i, (_, row) in enumerate(sub.iterrows()):
        minutes = hour_start * 60 + i * 9
        h, m = divmod(minutes, 60)
        orders.append(
            {
                "order_id": f"{prefix}-{i:03d}",
                "lat_wgs84": round(float(row.lat_wgs84), 6),
                "lon_wgs84": round(float(row.lon_wgs84), 6),
                "city_name": city,
                "ds": ds,
                "delivery_day": delivery_day,
                "receipt_time": f"{delivery_day} {h % 24:02d}:{m:02d}:00",
                "typecode": row.typecode,
                "aoi_id": row.aoi_id,
                "receipt_lat_wgs84": round(rlat, 6),
                "receipt_lon_wgs84": round(rlon, 6),
                "notes": f"cluster={cluster_id}; courier={courier_id[:8]}",
            }
        )
    return orders


def register_courier(
    registry: dict,
    courier_id: str,
    city: str,
    ds: int,
) -> None:
    key = (courier_id, city, ds)
    if key in registry:
        return
    slat, slon = courier_start(courier_id, city, DS)
    registry[key] = {
        "courier_id": courier_id,
        "city_name": city,
        "ds": ds,
        "start_lat_wgs84": round(slat, 6),
        "start_lon_wgs84": round(slon, 6),
    }


# (city, cluster_id, n_orders, prefix, hour_start, ds, delivery_day, seed)
SCENARIOS = [
    ("Chongqing", 252, 8, "cq-a", 8, DS, DAY, 1),
    ("Chongqing", 253, 6, "cq-b", 8, DS, DAY, 2),
    ("Chongqing", 258, 5, "cq-c", 9, DS, DAY, 3),
    ("Shanghai", 4, 7, "sh-a", 8, DS, DAY, 4),
    ("Shanghai", 1, 6, "sh-b", 8, DS, DAY, 5),
    ("Shanghai", 3, 5, "sh-c", 9, DS, DAY, 6),
    ("Hangzhou", 694, 7, "hz-a", 8, DS, DAY, 7),
    ("Hangzhou", 692, 5, "hz-b", 9, DS, DAY, 8),
    ("Chongqing", 252, 4, "cq-a2", 8, DS2, DAY2, 11),
    ("Shanghai", 4, 4, "sh-a2", 8, DS2, DAY2, 12),
]

all_orders: list[dict] = []
courier_registry: dict = {}

for city, cid, n, prefix, h0, ds, dday, seed in SCENARIOS:
    assign_ds = DS if ds == DS2 and ca[(ca.city_name == city) & (ca.cluster_id == cid) & (ca.ds == DS2)].empty else ds
    courier_id = resolve_courier(city, cid, assign_ds)
    order_ds = ds
    if ds == DS2:
        pool319 = df[(df.city_name == city) & (df.cluster_id == cid) & (df.ds == DS2)]
        order_ds = DS2 if len(pool319) >= n else DS
    register_courier(courier_registry, courier_id, city, ds)
    all_orders.extend(
        sample_cluster_orders(
            city, cid, n, prefix, courier_id, ds=order_ds, delivery_day=dday, hour_start=h0, seed=seed
        )
    )

# Beijing courier (manual coords — tests nearest-courier without historical clusters)
beijing_courier = "66907539947b192650558694485996b6"
beijing_stops = [
    (39.9042, 116.4074, "203ac3454d75e02ebb0a3c6f51d735e4", "bj-aoi-001"),
    (39.918, 116.42, "203ac3454d75e02ebb0a3c6f51d735e4", "bj-aoi-002"),
    (39.89, 116.38, "fe76dff35bb199cdb7329eba2b918f18", "bj-aoi-003"),
    (39.928, 116.445, "203ac3454d75e02ebb0a3c6f51d735e4", "bj-aoi-004"),
    (39.915, 116.39, "203ac3454d75e02ebb0a3c6f51d735e4", "bj-aoi-005"),
]
for i, (lat, lon, tc, aoi) in enumerate(beijing_stops):
    all_orders.append(
        {
            "order_id": f"bj-{i:03d}",
            "lat_wgs84": lat,
            "lon_wgs84": lon,
            "city_name": "Beijing",
            "ds": DS,
            "delivery_day": DAY,
            "receipt_time": f"{DAY} {10 + i // 2:02d}:{(i * 11) % 60:02d}:00",
            "typecode": tc,
            "aoi_id": aoi,
            "receipt_lat_wgs84": 39.90872,
            "receipt_lon_wgs84": 116.39749,
            "notes": "Beijing courier pool; nearest-courier assignment",
        }
    )
courier_registry[(beijing_courier, "Beijing", DS)] = {
    "courier_id": beijing_courier,
    "city_name": "Beijing",
    "ds": DS,
    "start_lat_wgs84": 39.90872,
    "start_lon_wgs84": 116.39749,
}

# Edge: wrong city label vs coords
row = df[(df.city_name == "Chongqing") & (df.cluster_id == 252) & (df.ds == DS)].iloc[5]
all_orders.append(
    {
        "order_id": "edge-001",
        "lat_wgs84": round(float(row.lat_wgs84), 6),
        "lon_wgs84": round(float(row.lon_wgs84), 6),
        "city_name": "Shanghai",
        "ds": DS,
        "delivery_day": DAY,
        "receipt_time": f"{DAY} 14:30:00",
        "typecode": row.typecode,
        "aoi_id": row.aoi_id,
        "receipt_lat_wgs84": 31.2304,
        "receipt_lon_wgs84": 121.4737,
        "notes": "Edge: Shanghai label, Chongqing-area delivery coords",
    }
)

# Hangzhou solo / distant order
all_orders.append(
    {
        "order_id": "hz-solo-001",
        "lat_wgs84": 30.25,
        "lon_wgs84": 120.15,
        "city_name": "Hangzhou",
        "ds": DS,
        "delivery_day": DAY,
        "receipt_time": f"{DAY} 15:00:00",
        "typecode": "203ac3454d75e02ebb0a3c6f51d735e4",
        "aoi_id": "34bff3d04c92e20bca943a693597b671",
        "receipt_lat_wgs84": 30.2741,
        "receipt_lon_wgs84": 120.1551,
        "notes": "Distant Hangzhou stop; may assign as noise or far cluster",
    }
)

couriers = list(courier_registry.values())

(DATA_DIR / "synthetic_orders.json").write_text(
    json.dumps(all_orders, indent=2, ensure_ascii=False), encoding="utf-8"
)
(DATA_DIR / "synthetic_couriers.json").write_text(
    json.dumps(couriers, indent=2, ensure_ascii=False), encoding="utf-8"
)

print(f"Wrote {len(all_orders)} orders, {len(couriers)} couriers")
from collections import Counter

for (city, ds), cnt in sorted(Counter((o["city_name"], o["ds"]) for o in all_orders).items()):
    print(f"  {city} ds={ds}: {cnt} orders")
