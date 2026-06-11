"""One-off generator for synthetic_orders.json and synthetic_couriers.json.

Sources hub coordinates directly from Supabase hubs.lat / hubs.lng — no conversion.

Run from repo root:
    python ml_services/route_prediction/full_pipeline/data/_generate_samples.py
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from rag.supabase.supabase_connection import get_supabase_engine  # noqa: E402

DATA_DIR = Path(__file__).parent
DAY1 = "2026-06-03"
DAY2 = "2026-06-04"
DS = 318


def load_hubs() -> pd.DataFrame:
    """Load hubs from Supabase using the current schema (lat/lng, no conversion)."""
    engine = get_supabase_engine()
    df = pd.read_sql(
        """
        SELECT h.hub_id,
               h.hub_name AS name,
               h.lat,
               h.lng,
               h.representative_typecode AS typecode,
               h.representative_aoi_id   AS aoi_id,
               c.city_name
        FROM hubs h
        JOIN cities c ON h.city_id = c.city_id
        ORDER BY h.hub_id
        """,
        engine,
    )
    df = df.where(pd.notnull(df), None)
    # Keep *_wgs84 aliases so _order/_courier output dicts are unchanged
    df["lat_wgs84"] = df["lat"]
    df["lon_wgs84"] = df["lng"]
    return df


def _order(
    order_id: str,
    from_hub: pd.Series,
    to_hub: pd.Series,
    city: str,
    delivery_day: str,
    hour: int = 8,
) -> dict:
    return {
        "order_id": order_id,
        "from_hub_name": from_hub["name"],
        "to_hub_name": to_hub["name"],
        "receipt_lat_wgs84": from_hub["lat_wgs84"],
        "receipt_lon_wgs84": from_hub["lon_wgs84"],
        "lat_wgs84": to_hub["lat_wgs84"],
        "lon_wgs84": to_hub["lon_wgs84"],
        "city_name": city,
        "ds": DS,
        "delivery_day": delivery_day,
        "receipt_time": f"{delivery_day} {hour:02d}:00:00",
        "typecode": from_hub.get("typecode") or "110000",
        "aoi_id": from_hub.get("aoi_id") or "",
        "notes": f"from={from_hub['name']}; to={to_hub['name']}",
    }


def _courier(courier_id: str, hub: pd.Series, city: str) -> dict:
    return {
        "courier_id": courier_id,
        "city_name": city,
        "hub_name": hub["name"],
        "start_lat_wgs84": hub["lat_wgs84"],
        "start_lon_wgs84": hub["lon_wgs84"],
    }


def build_scenarios(hubs: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    orders: list[dict] = []
    couriers: list[dict] = []
    courier_registry: dict[str, str] = {}

    def get_or_create_courier(hub: pd.Series, city: str) -> str:
        key = f"{city}:{hub['name']}"
        if key not in courier_registry:
            cid = uuid.uuid4().hex
            courier_registry[key] = cid
            couriers.append(_courier(cid, hub, city))
        return courier_registry[key]

    for city in ["Chongqing", "Shanghai", "Hangzhou"]:
        city_hubs = hubs[hubs["city_name"] == city].reset_index(drop=True)
        if len(city_hubs) < 3:
            continue

        h0, h1, h2, h3 = city_hubs.iloc[0], city_hubs.iloc[1], city_hubs.iloc[2], city_hubs.iloc[min(3, len(city_hubs) - 1)]
        get_or_create_courier(h0, city)
        get_or_create_courier(h2, city)

        for i in range(4):
            orders.append(_order(f"{city[:2].lower()}-a-{i:03d}", h0, h1, city, DAY1, hour=8 + i))
        for i in range(3):
            orders.append(_order(f"{city[:2].lower()}-b-{i:03d}", h1, h2, city, DAY1, hour=9 + i))
        for i in range(3):
            orders.append(_order(f"{city[:2].lower()}-c-{i:03d}", h2, h3, city, DAY1, hour=10 + i))
        for i in range(2):
            orders.append(_order(f"{city[:2].lower()}-d2-{i:03d}", h0, h3, city, DAY2, hour=8 + i))

    # Jilin (smaller city — may only have a few hubs)
    jilin_hubs = hubs[hubs["city_name"] == "Jilin"].reset_index(drop=True)
    if len(jilin_hubs) >= 2:
        h0, h1 = jilin_hubs.iloc[0], jilin_hubs.iloc[1]
        get_or_create_courier(h0, "Jilin")
        for i in range(3):
            orders.append(_order(f"jl-a-{i:03d}", h0, h1, "Jilin", DAY1, hour=8 + i))

    return orders, couriers


def main() -> None:
    print("Loading hubs from Supabase …")
    hubs = load_hubs()
    print(f"  {len(hubs)} hubs across {hubs['city_name'].nunique()} cities")

    orders, couriers = build_scenarios(hubs)

    orders_path = DATA_DIR / "synthetic_orders.json"
    couriers_path = DATA_DIR / "synthetic_couriers.json"

    with open(orders_path, "w", encoding="utf-8") as f:
        json.dump(orders, f, indent=2, ensure_ascii=False)
    with open(couriers_path, "w", encoding="utf-8") as f:
        json.dump(couriers, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(orders)} orders  → {orders_path}")
    print(f"Wrote {len(couriers)} couriers → {couriers_path}")


if __name__ == "__main__":
    main()
