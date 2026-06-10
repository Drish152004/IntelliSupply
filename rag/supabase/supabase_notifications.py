from typing import Any
from sqlalchemy import text
from rag.supabase.supabase_connection import get_supabase_engine

def _engine():
    return get_supabase_engine()

def create_notification(
    *,
    title: str,
    message: str,
    alert_type: str,
    severity: str = "medium",
    target_role: str | None = None,
    target_user_id: str | None = None,
    related_entity_type: str | None = None,
    related_entity_id: str | None = None,
    source: str = "system",
    dedupe_key: str | None = None,
) -> dict[str, Any] | None:
    query = text(
        """
        INSERT INTO notifications (
            title,
            message,
            alert_type,
            severity,
            target_role,
            target_user_id,
            related_entity_type,
            related_entity_id,
            source,
            dedupe_key
        )
        VALUES (
            :title,
            :message,
            :alert_type,
            :severity,
            :target_role,
            :target_user_id,
            :related_entity_type,
            :related_entity_id,
            :source,
            :dedupe_key
        )
        ON CONFLICT (dedupe_key)
        WHERE dedupe_key IS NOT NULL
        DO NOTHING
        RETURNING *
        """
    )

    with _engine().begin() as conn:
        row = conn.execute(
            query,
            {
                "title": title,
                "message": message,
                "alert_type": alert_type,
                "severity": severity,
                "target_role": target_role,
                "target_user_id": target_user_id,
                "related_entity_type": related_entity_type,
                "related_entity_id": related_entity_id,
                "source": source,
            },
        ).mappings().first()

    return dict(row) if row else None

def list_notifications_for_user(
    *,
    user_id: str,
    role: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    query = text(
        """
        SELECT *
        FROM notifications
        WHERE
            target_user_id::text = :user_id
            OR target_role = :role
            OR target_role IS NULL
        ORDER BY created_at DESC
        LIMIT :limit
        """
    )

    with _engine().connect() as conn:
        rows = conn.execute(
            query,
            {
                "user_id": str(user_id),
                "role": role,
                "limit": int(limit),
            },
        ).mappings().all()

    return [dict(row) for row in rows]

def mark_notification_read(notification_id: str) -> dict[str, Any] | None:
    query = text(
        """
        UPDATE notifications
        SET is_read = true
        WHERE notification_id::text = :notification_id
        RETURNING *
        """
    )

    with _engine().begin() as conn:
        row = conn.execute(
            query,
            {"notification_id": str(notification_id)},
        ).mappings().first()

    return dict(row) if row else None

def mark_all_notifications_read(
    *,
    user_id: str,
    role: str,
) -> int:
    query = text(
        """
        UPDATE notifications
        SET is_read = true
        WHERE is_read = false
          AND (
              target_user_id::text = :user_id
              OR target_role = :role
              OR target_role IS NULL
          )
        """
    )

    with _engine().begin() as conn:
        result = conn.execute(
            query,
            {
                "user_id": str(user_id),
                "role": role,
            },
        )

    return int(result.rowcount or 0)

def get_unread_count(
    *,
    user_id: str,
    role: str,
) -> int:
    query = text(
        """
        SELECT count(*)
        FROM notifications
        WHERE is_read = false
          AND (
              target_user_id::text = :user_id
              OR target_role = :role
              OR target_role IS NULL
          )
        """
    )

    with _engine().connect() as conn:
        count = conn.execute(
            query,
            {
                "user_id": str(user_id),
                "role": role,
            },
        ).scalar()

    return int(count or 0)

def delete_notification(notification_id: str) -> bool:
    query = text(
        """
        DELETE FROM notifications
        WHERE notification_id::text = :notification_id
        """
    )

    with _engine().begin() as conn:
        result = conn.execute(
            query,
            {"notification_id": str(notification_id)},
        )

    return bool(result.rowcount)