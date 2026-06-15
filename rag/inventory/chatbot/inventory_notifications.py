"""Inventory notification service using inventory project database."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import text


def _engine():
    """
    Use the same DB connection as inventory products/summary.

    This should point to the database that contains:
    - planning_dataset
    - product_catalog
    - hubs
    """
    from chatbot.database import engine

    return engine


def ensure_inventory_notifications_table() -> None:
    """
    Create inventory_notifications table inside the inventory database.

    This keeps inventory notifications separate from logistics notifications.
    """
    query = text(
        """
        CREATE TABLE IF NOT EXISTS inventory_notifications (
            notification_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL DEFAULT 'medium',

            target_role TEXT,
            target_user_id TEXT,

            related_entity_type TEXT,
            related_entity_id TEXT,

            source TEXT NOT NULL DEFAULT 'inventory_service',
            dedupe_key TEXT UNIQUE,

            is_read BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    with _engine().begin() as conn:
        conn.execute(query)


def create_inventory_notification(
    *,
    title: str,
    message: str,
    alert_type: str,
    severity: str = "medium",
    target_role: str | None = "inventory_manager",
    target_user_id: str | None = None,
    related_entity_type: str | None = None,
    related_entity_id: str | None = None,
    source: str = "inventory_service",
    dedupe_key: str | None = None,
) -> dict[str, Any] | None:
    ensure_inventory_notifications_table()

    notification_id = str(uuid.uuid4())

    query = text(
        """
        INSERT INTO inventory_notifications (
            notification_id,
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
            :notification_id,
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
        DO NOTHING
        RETURNING *
        """
    )

    with _engine().begin() as conn:
        row = conn.execute(
            query,
            {
                "notification_id": notification_id,
                "title": title,
                "message": message,
                "alert_type": alert_type,
                "severity": severity,
                "target_role": target_role,
                "target_user_id": target_user_id,
                "related_entity_type": related_entity_type,
                "related_entity_id": related_entity_id,
                "source": source,
                "dedupe_key": dedupe_key,
            },
        ).mappings().first()

    return dict(row) if row else None


def generate_inventory_notifications(limit: int = 10) -> int:
    """
    Generate hub-level inventory notifications from latest planning_dataset data.

    Creates alerts for:
    - stockout: inventory_level <= 0 at a hub
    - demand risk: inventory_level < demand at a hub
    - low buffer: inventory_level < 20 at a hub

    Each notification mentions the hub.
    """
    ensure_inventory_notifications_table()

    query = text(
        """
        WITH latest_date AS (
            SELECT MAX(date) AS latest_date
            FROM planning_dataset
        ),
        latest_inventory AS (
            SELECT
                pd.date,
                pd.hub_id,
                h.hub_name,
                pd.product_id,
                pd.category,
                COALESCE(
                    pc.product_display_name,
                    pc.product_name,
                    pd.product_id
                ) AS product_name,
                COALESCE(SUM(pd.inventory_level), 0) AS total_stock,
                COALESCE(SUM(pd.demand), 0) AS total_demand
            FROM planning_dataset pd
            JOIN latest_date ld
                ON pd.date = ld.latest_date
            LEFT JOIN product_catalog pc
                ON pc.product_id = pd.product_id
               AND pc.category = pd.category
            LEFT JOIN hubs h
                ON h.hub_id = pd.hub_id
            GROUP BY
                pd.date,
                pd.hub_id,
                h.hub_name,
                pd.product_id,
                pd.category,
                pc.product_display_name,
                pc.product_name
        )
        SELECT
            date,
            hub_id,
            hub_name,
            product_id,
            category,
            product_name,
            total_stock,
            total_demand
        FROM latest_inventory
        WHERE
            total_stock <= 0
            OR total_stock < total_demand
            OR total_stock < 20
        ORDER BY
            CASE
                WHEN total_stock <= 0 THEN 0
                WHEN total_stock < total_demand THEN 1
                ELSE 2
            END,
            total_stock ASC
        LIMIT :limit
        """
    )

    with _engine().connect() as conn:
        rows = conn.execute(query, {"limit": int(limit)}).mappings().all()

    created_count = 0

    for row in rows:
        latest_date = row["date"]
        hub_id = row["hub_id"]
        hub_name = row["hub_name"] or f"Hub {hub_id}"
        product_id = row["product_id"]
        category = row["category"]
        product_name = row["product_name"]
        stock = int(row["total_stock"] or 0)
        demand = int(row["total_demand"] or 0)

        product_label = f"{product_name} ({product_id})"

        if stock <= 0:
            title = "Stockout alert"
            severity = "critical"
            message = (
                f"{product_label} is out of stock at {hub_name}."
            )
        elif demand > 0 and stock < demand:
            title = "Demand exceeds inventory"
            severity = "high"
            message = (
                f"{product_label} at {hub_name} has {stock} units available, "
                f"below demand of {demand} units."
            )
        else:
            title = "Low stock alert"
            severity = "medium"
            message = (
                f"{product_label} at {hub_name} has only {stock} units available."
            )

        dedupe_key = (
            f"inventory:{latest_date}:hub:{hub_id}:"
            f"{product_id}:{category}:{title}"
        )

        created = create_inventory_notification(
            title=title,
            message=message,
            alert_type="inventory",
            severity=severity,
            target_role="inventory_manager",
            target_user_id=None,
            related_entity_type="product_hub",
            related_entity_id=f"{product_id}::{category}::hub:{hub_id}",
            source="inventory_service",
            dedupe_key=dedupe_key,
        )

        if created:
            created_count += 1

    return created_count


def list_inventory_notifications_for_user(
    *,
    user_id: str,
    role: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    ensure_inventory_notifications_table()

    query = text(
        """
        SELECT *
        FROM inventory_notifications
        WHERE
            target_user_id::text = :user_id
            OR target_role = :role
            OR target_role IS NULL
            OR (:is_admin = true AND target_role = 'inventory_manager')
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
                "is_admin": role == "admin",
                "limit": int(limit),
            },
        ).mappings().all()

    return [dict(row) for row in rows]


def get_inventory_unread_count(
    *,
    user_id: str,
    role: str,
) -> int:
    ensure_inventory_notifications_table()

    query = text(
        """
        SELECT COUNT(*)
        FROM inventory_notifications
        WHERE is_read = false
          AND (
              target_user_id::text = :user_id
              OR target_role = :role
              OR target_role IS NULL
              OR (:is_admin = true AND target_role = 'inventory_manager')
          )
        """
    )

    with _engine().connect() as conn:
        count = conn.execute(
            query,
            {
                "user_id": str(user_id),
                "role": role,
                "is_admin": role == "admin",
            },
        ).scalar()

    return int(count or 0)


def mark_inventory_notification_read(
    notification_id: str,
) -> dict[str, Any] | None:
    ensure_inventory_notifications_table()

    query = text(
        """
        UPDATE inventory_notifications
        SET
            is_read = true,
            updated_at = NOW()
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


def mark_all_inventory_notifications_read(
    *,
    user_id: str,
    role: str,
) -> int:
    ensure_inventory_notifications_table()

    query = text(
        """
        UPDATE inventory_notifications
        SET
            is_read = true,
            updated_at = NOW()
        WHERE is_read = false
          AND (
              target_user_id::text = :user_id
              OR target_role = :role
              OR target_role IS NULL
              OR (:is_admin = true AND target_role = 'inventory_manager')
          )
        """
    )

    with _engine().begin() as conn:
        result = conn.execute(
            query,
            {
                "user_id": str(user_id),
                "role": role,
                "is_admin": role == "admin",
            },
        )

    return int(result.rowcount or 0)
