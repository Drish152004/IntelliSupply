"""Derived operational notifications."""

from __future__ import annotations

from typing import Any

from aura_graphdb.aura_route_queries import get_recent_order_routes

from services import inventory as inventory_svc


def list_notifications(*, role: str, limit: int = 20) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    if role in {"admin", "inventory_manager"} and inventory_svc.inventory_db_available():
        try:
            summary = inventory_svc.get_summary()
            for index, signal in enumerate(summary.get("risk_signals", [])[:5]):
                items.append(
                    {
                        "id": f"NTF-INV-{index + 1:03d}",
                        "title": signal["title"],
                        "description": signal["description"],
                        "category": "Inventory",
                        "severity": signal["severity"],
                        "location": "Warehouse network",
                        "time": "recent",
                        "status": "Restock" if signal["severity"] == "Critical" else "Review",
                        "unread": True,
                    }
                )
        except Exception:
            pass

    if role in {"admin", "logistics_manager"}:
        try:
            shipments = get_recent_order_routes(limit=5)
            for index, shipment in enumerate(shipments):
                items.append(
                    {
                        "id": f"NTF-LOG-{index + 1:03d}",
                        "title": f"Shipment {shipment.get('order_id')} assigned",
                        "description": (
                            f"Route {shipment.get('from_hub_name')} → {shipment.get('to_hub_name')} "
                            f"assigned to {shipment.get('assigned_courier_name') or 'courier'}."
                        ),
                        "category": "Dispatch",
                        "severity": "Medium",
                        "location": shipment.get("city_name") or "Logistics network",
                        "time": "recent",
                        "status": "Review",
                        "unread": True,
                    }
                )
        except Exception:
            pass

    return items[:limit]
