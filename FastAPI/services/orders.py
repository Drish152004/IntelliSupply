"""Order creation service."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo
from rag.supabase.supabase_notifications import create_notification
from rag.aura_graphdb.aura_order import create_order_and_assign_nearest_courier
from rag.aura_graphdb.aura_route_prediction import delete_ml_courier_route


def _resolve_receipt_time(delivery_date: str, receipt_time: str | None) -> str:
    if receipt_time:
        return f"{delivery_date} {receipt_time}"
    return datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")


def _sanitize_record(record: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for key, value in record.items():
        if value is None:
            out[key] = None
        elif hasattr(value, "iso_format"):
            out[key] = value.iso_format()
        elif hasattr(value, "isoformat"):
            out[key] = value.isoformat()
        else:
            out[key] = value
    return out


def create_shipment(payload: dict[str, Any]) -> dict[str, Any]:
    receipt_time = _resolve_receipt_time(payload["delivery_date"], payload.get("receipt_time"))

    order_result = create_order_and_assign_nearest_courier(
        from_hub_name=payload["from_hub_name"],
        to_hub_name=payload["to_hub_name"],
        delivery_day=payload["delivery_date"],
        receipt_time=receipt_time,
        extra_notes=payload.get("notes"),
    )

    if not order_result.get("success"):
        return {
            "success": False,
            "message": order_result.get("message", "Order creation failed."),
            "order": None,
        }

    order = _sanitize_record(order_result["order"])
    try:
        _notify_shipment_created(order)
    except Exception as exc:
        print(f"Shipment notification skipped: {exc}")
    # Invalidate any persisted route prediction for the assigned courier/day
    try:
        assigned_cid = order.get("assigned_courier_id")
        if assigned_cid and order.get("delivery_day"):
            try:
                delete_ml_courier_route(courier_id=assigned_cid, delivery_day=order.get("delivery_day"))
            except Exception:
                # best-effort invalidation; don't block order creation
                pass
    except Exception:
        pass

    return {
        "success": True,
        "message": order_result["message"],
        "order": order,
    }
def _notify_shipment_created(order: dict[str, Any]) -> None:
    order_id = order.get("order_id")
    if not order_id:
        return

    from_hub = order.get("from_hub_name") or "source hub"
    to_hub = order.get("to_hub_name") or "destination hub"
    courier_name = (
        order.get("assigned_courier_name")
        or order.get("assigned_courier_id")
        or "nearest courier"
    )

    for role in ("admin", "logistics_manager"):
        create_notification(
            title="Shipment created",
            message=(
                f"Order {order_id} from {from_hub} to {to_hub} "
                f"was assigned to {courier_name}."
            ),
            alert_type="order_created",
            severity="medium",
            target_role=role,
            related_entity_type="order",
            related_entity_id=str(order_id),
            source="logistics_crud",
            dedupe_key=f"order_created:{order_id}:{role}",
        )

    assigned_courier_id = order.get("assigned_courier_id")
    if assigned_courier_id:
        create_notification(
            title="New shipment assigned",
            message=f"You have been assigned order {order_id} from {from_hub} to {to_hub}.",
            alert_type="shipment_assigned",
            severity="medium",
            target_role="courier",
            target_user_id=None,
            related_entity_type="order",
            related_entity_id=str(order_id),
            source="logistics_crud",
            dedupe_key=f"shipment_assigned:{order_id}:{assigned_courier_id}",
        )