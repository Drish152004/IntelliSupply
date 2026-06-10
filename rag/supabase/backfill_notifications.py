from rag.aura_graphdb.aura_route_queries import get_recent_order_routes
from rag.supabase.supabase_inventory import get_low_stock_inventory
from rag.supabase.supabase_notifications import create_notification

def backfill_order_notifications(limit: int = 100) -> int:
    orders = get_recent_order_routes(limit=limit)
    created_count = 0

    for order in orders:
        order_id = order["order_id"]

        for role in ["admin", "logistics_manager"]:
            notification = create_notification(
                title="Shipment assigned",
                message=(
                    f"Order {order_id} from {order.get('from_hub_name')} "
                    f"to {order.get('to_hub_name')} was assigned to "
                    f"{order.get('assigned_courier_name') or 'courier'}."
                ),
                alert_type="order_created",
                severity="medium",
                target_role=role,
                related_entity_type="order",
                related_entity_id=order_id,
                source="backfill_graphdb",
                dedupe_key=f"order_created:{order_id}:{role}",
            )

            if notification:
                created_count += 1

    return created_count


def backfill_inventory_notifications(limit: int = 100) -> int:
    inventory_items = get_low_stock_inventory(limit=limit)
    created_count = 0

    for item in inventory_items:
        inventory_id = item["inventory_id"]
        product_name = item.get("product_name") or item.get("product_id")
        product_id = item.get("product_id")
        hub_id = item.get("hub_id")
        quantity = item.get("quantity")
        threshold = item.get("threshold_limit")

        if quantity is not None and quantity <= 0:
            title = "Product stockout"
            alert_type = "stockout"
            severity = "critical"
            message = (
                f"{product_name} is out of stock at hub {hub_id}. "
                f"Current quantity is {quantity}, threshold limit is {threshold}."
            )
        else:
            title = "Low inventory alert"
            alert_type = "low_stock"
            severity = "high"
            message = (
                f"{product_name} is below threshold at hub {hub_id}. "
                f"Current quantity is {quantity}, threshold limit is {threshold}."
            )

        for role in ["admin", "inventory_manager"]:
            notification = create_notification(
                title=title,
                message=message,
                alert_type=alert_type,
                severity=severity,
                target_role=role,
                related_entity_type="inventory",
                related_entity_id=inventory_id,
                source="backfill_supabase_inventory",
                dedupe_key=f"{alert_type}:{inventory_id}:{product_id}:{hub_id}:{role}",
            )

            if notification:
                created_count += 1

    return created_count


def backfill_all_notifications() -> dict:
    order_count = backfill_order_notifications(limit=100)
    inventory_count = backfill_inventory_notifications(limit=100)

    return {
        "order_notifications_created": order_count,
        "inventory_notifications_created": inventory_count,
        "total_created": order_count + inventory_count,
    }


if __name__ == "__main__":
    result = backfill_all_notifications()
    print(result)