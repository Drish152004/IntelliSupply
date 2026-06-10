"""Supabase-backed operational notification service."""
from rag.supabase.supabase_notifications import mark_all_notifications_read
from __future__ import annotations
from typing import Any
from rag.supabase.supabase_notifications import (
    get_unread_count,
    list_notifications_for_user,
    mark_notification_read,
)

def list_notifications(
    *,
    user_id: str,
    role: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    return list_notifications_for_user(
        user_id=user_id,
        role=role,
        limit=limit,
    )

def unread_count(
    *,
    user_id: str,
    role: str,
) -> int:
    return get_unread_count(
        user_id=user_id,
        role=role,
    )

def mark_as_read(notification_id: str) -> dict[str, Any] | None:
    return mark_notification_read(notification_id)

def mark_all_as_read(
    *,
    user_id: str,
    role: str,
) -> int:
    return mark_all_notifications_read(
        user_id=user_id,
        role=role,
    )