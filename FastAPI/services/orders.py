"""Order creation service."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from aura_graphdb.aura_order import create_order_and_assign_nearest_courier


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

    return {
        "success": True,
        "message": order_result["message"],
        "order": order,
    }
