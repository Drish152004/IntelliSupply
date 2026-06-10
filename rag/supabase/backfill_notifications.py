from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RAG_ROOT = _REPO_ROOT / "rag"
for path in (_REPO_ROOT, _RAG_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from config.env import load_env

load_env()

from rag.aura_graphdb.aura_route_queries import get_recent_order_routes
from rag.supabase.supabase_notifications import create_notification


def backfill_order_notifications(limit: int = 100):
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


if __name__ == "__main__":
    created = backfill_order_notifications()
    print(f"Backfill complete. Created {created} notifications.")