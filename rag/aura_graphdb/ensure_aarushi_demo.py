"""Ensure demo courier Aarushi and sample Shanghai orders exist in Aura."""

from __future__ import annotations

from datetime import date

from aura_graphdb.aura_connection import AuraConnection
from aura_graphdb.aura_courier import create_courier_node, get_courier_by_email

AARUSHI_EMAIL = "aarushi_courier@intellisupply.com"
AARUSHI_NAME = "Aarushi"
AARUSHI_COURIER_ID = "aarushi_demo_courier"
AARUSHI_CITY = "Shanghai"
AARUSHI_HUB = "Hub 1"

DEMO_ORDERS = [
    ("ord-demo-aa-0615-01", "Hub 1", "Hub 12"),
    ("ord-demo-aa-0615-02", "Hub 1", "Hub 16"),
    ("ord-demo-aa-0615-03", "Hub 12", "Hub 19"),
]


def ensure_aarushi_courier() -> dict:
    existing = get_courier_by_email(AARUSHI_EMAIL)
    if existing:
        return existing

    result = create_courier_node(
        name=AARUSHI_NAME,
        email=AARUSHI_EMAIL,
        city_name=AARUSHI_CITY,
        hub_name=AARUSHI_HUB,
        courier_id=AARUSHI_COURIER_ID,
    )
    if not result.get("success") and "courier" not in result:
        raise RuntimeError(result.get("message", "Failed to create Aarushi courier."))
    return result.get("courier") or get_courier_by_email(AARUSHI_EMAIL) or {}


def ensure_aarushi_orders(delivery_day: str | None = None) -> list[str]:
    delivery_day = delivery_day or date.today().isoformat()
    courier = ensure_aarushi_courier()
    courier_id = courier.get("courier_id") or AARUSHI_COURIER_ID

    conn = AuraConnection()
    created: list[str] = []

    query = """
    MATCH (from_hub:Hub {name: $from_hub_name})-[:LOCATED_IN]->(city:City)
    MATCH (to_hub:Hub {name: $to_hub_name})-[:LOCATED_IN]->(city)
    MATCH (courier:Courier {courier_id: $courier_id})-[:OPERATES_IN]->(city)
    MERGE (order:Order {order_id: $order_id})
    ON CREATE SET
        order.created_at = datetime(),
        order.lat_wgs84 = toFloat(to_hub.lat),
        order.lon_wgs84 = toFloat(to_hub.lng),
        order.receipt_lat_wgs84 = toFloat(from_hub.lat),
        order.receipt_lon_wgs84 = toFloat(from_hub.lng)
    SET
        order.city_name = city.city_name,
        order.ds = toInteger($ds),
        order.delivery_day = $delivery_day,
        order.receipt_time = $receipt_time,
        order.typecode = coalesce(to_hub.representative_typecode, 1),
        order.aoi_id = coalesce(to_hub.representative_aoi_id, 0),
        order.from_hub_name = from_hub.name,
        order.to_hub_name = to_hub.name,
        order.assigned_courier_id = courier.courier_id,
        order.nearest_courier_distance_m = 0.0,
        order.updated_at = datetime()
    MERGE (order)-[:FROM_HUB]->(from_hub)
    MERGE (order)-[:TO_HUB]->(to_hub)
    MERGE (order)-[:BELONGS_TO_CITY]->(city)
    MERGE (order)-[:ASSIGNED_TO]->(courier)
    RETURN order.order_id AS order_id
    """

    try:
        for order_id, from_hub, to_hub in DEMO_ORDERS:
            rows = conn.execute_write(
                query,
                {
                    "order_id": order_id,
                    "from_hub_name": from_hub,
                    "to_hub_name": to_hub,
                    "courier_id": courier_id,
                    "delivery_day": delivery_day,
                    "receipt_time": f"{delivery_day} 09:00:00",
                    "ds": 318,
                },
            )
            if rows:
                created.append(rows[0]["order_id"])
    finally:
        conn.close()

    return created


def main() -> None:
    day = date.today().isoformat()
    courier = ensure_aarushi_courier()
    orders = ensure_aarushi_orders(day)
    print(f"Aarushi courier: {courier.get('courier_id')} ({courier.get('email')})")
    print(f"Demo orders on {day}: {orders}")


if __name__ == "__main__":
    main()
