"""Operational notification service.

Logistics notifications and inventory notifications are stored separately.

- Logistics notifications use rag.supabase.supabase_notifications
- Inventory notifications use rag.inventory.chatbot.inventory_notifications
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from rag.supabase.supabase_notifications import (
    get_unread_count as get_logistics_unread_count,
    list_notifications_for_user as list_logistics_notifications_for_user,
    mark_all_notifications_read as mark_all_logistics_notifications_read,
    mark_notification_read as mark_logistics_notification_read,
)

from rag.inventory.chatbot.inventory_notifications import (
    generate_inventory_notifications,
    get_inventory_unread_count,
    list_inventory_notifications_for_user,
    mark_all_inventory_notifications_read,
    mark_inventory_notification_read,
)


def _created_at_value(item: dict[str, Any]):
    value = item.get("created_at")

    if isinstance(value, datetime):
        return value

    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.min

    return datetime.min


def list_notifications(
    *,
    user_id: str,
    role: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    if role in {"admin", "inventory_manager"}:
        try:
            generate_inventory_notifications(limit=10)
            items.extend(
                list_inventory_notifications_for_user(
                    user_id=user_id,
                    role=role,
                    limit=limit,
                )
            )
        except Exception as exc:
            print(f"Inventory notification load skipped: {exc}")

    if role in {"admin", "logistics_manager", "courier"}:
        try:
            items.extend(
                list_logistics_notifications_for_user(
                    user_id=user_id,
                    role=role,
                    limit=limit,
                )
            )
        except Exception as exc:
            print(f"Logistics notification load skipped: {exc}")

    items.sort(key=_created_at_value, reverse=True)
    return items[:limit]


def unread_count(
    *,
    user_id: str,
    role: str,
) -> int:
    total = 0

    if role in {"admin", "inventory_manager"}:
        try:
            generate_inventory_notifications(limit=10)
            total += get_inventory_unread_count(
                user_id=user_id,
                role=role,
            )
        except Exception as exc:
            print(f"Inventory unread count skipped: {exc}")

    if role in {"admin", "logistics_manager", "courier"}:
        try:
            total += get_logistics_unread_count(
                user_id=user_id,
                role=role,
            )
        except Exception as exc:
            print(f"Logistics unread count skipped: {exc}")

    return total


def mark_as_read(notification_id: str) -> dict[str, Any] | None:
    try:
        notification = mark_inventory_notification_read(notification_id)
        if notification:
            return notification
    except Exception as exc:
        print(f"Inventory mark read skipped: {exc}")

    try:
        notification = mark_logistics_notification_read(notification_id)
        if notification:
            return notification
    except Exception as exc:
        print(f"Logistics mark read skipped: {exc}")

    return None


def mark_all_as_read(
    *,
    user_id: str,
    role: str,
) -> int:
    updated_count = 0

    if role in {"admin", "inventory_manager"}:
        try:
            updated_count += mark_all_inventory_notifications_read(
                user_id=user_id,
                role=role,
            )
        except Exception as exc:
            print(f"Inventory mark all read skipped: {exc}")

    if role in {"admin", "logistics_manager", "courier"}:
        try:
            updated_count += mark_all_logistics_notifications_read(
                user_id=user_id,
                role=role,
            )
        except Exception as exc:
            print(f"Logistics mark all read skipped: {exc}")

    return updated_count