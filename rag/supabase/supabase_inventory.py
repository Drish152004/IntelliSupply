from typing import Any

from sqlalchemy import text

from rag.supabase.supabase_connection import get_supabase_engine


def _engine():
    return get_supabase_engine()


def list_products(limit: int = 100) -> list[dict[str, Any]]:
    query = text(
        """
        SELECT *
        FROM products
        ORDER BY product_name
        LIMIT :limit
        """
    )

    with _engine().connect() as conn:
        rows = conn.execute(query, {"limit": int(limit)}).mappings().all()

    return [dict(row) for row in rows]


def get_product_by_id(product_id: str) -> dict[str, Any] | None:
    query = text(
        """
        SELECT *
        FROM products
        WHERE product_id::text = :product_id
        LIMIT 1
        """
    )

    with _engine().connect() as conn:
        row = conn.execute(
            query,
            {"product_id": str(product_id)},
        ).mappings().first()

    return dict(row) if row else None


def get_inventory_by_hub(hub_id: str) -> list[dict[str, Any]]:
    query = text(
        """
        SELECT
            i.inventory_id,
            i.product_id,
            p.product_name,
            p.category,
            p.unit_price,
            p.supplier_name,
            i.hub_id,
            i.rep_dipan_id,
            i.quantity,
            i.threshold_limit,
            i.last_updated
        FROM inventory i
        JOIN products p
            ON p.product_id = i.product_id
        WHERE i.hub_id::text = :hub_id
        ORDER BY p.product_name
        """
    )

    with _engine().connect() as conn:
        rows = conn.execute(
            query,
            {"hub_id": str(hub_id)},
        ).mappings().all()

    return [dict(row) for row in rows]


def get_low_stock_items(threshold: int = 10) -> list[dict[str, Any]]:
    query = text(
        """
        SELECT
            i.inventory_id,
            i.product_id,
            p.product_name,
            p.category,
            p.unit_price,
            p.supplier_name,
            i.hub_id,
            i.rep_dipan_id,
            i.quantity,
            i.threshold_limit,
            i.last_updated
        FROM inventory i
        JOIN products p
            ON p.product_id = i.product_id
        WHERE i.quantity IS NOT NULL
          AND i.quantity <= :threshold
        ORDER BY i.quantity ASC
        """
    )

    with _engine().connect() as conn:
        rows = conn.execute(
            query,
            {"threshold": int(threshold)},
        ).mappings().all()

    return [dict(row) for row in rows]


def get_low_stock_inventory(limit: int = 100) -> list[dict[str, Any]]:
    query = text(
        """
        SELECT
            i.inventory_id,
            i.product_id,
            p.product_name,
            p.category,
            p.unit_price,
            p.supplier_name,
            i.hub_id,
            i.rep_dipan_id,
            i.quantity,
            i.threshold_limit,
            i.last_updated
        FROM inventory i
        JOIN products p
            ON p.product_id = i.product_id
        WHERE i.quantity IS NOT NULL
          AND i.threshold_limit IS NOT NULL
          AND i.quantity <= i.threshold_limit
        ORDER BY i.quantity ASC
        LIMIT :limit
        """
    )

    with _engine().connect() as conn:
        rows = conn.execute(
            query,
            {"limit": int(limit)},
        ).mappings().all()

    return [dict(row) for row in rows]


def get_stockout_inventory(limit: int = 100) -> list[dict[str, Any]]:
    query = text(
        """
        SELECT
            i.inventory_id,
            i.product_id,
            p.product_name,
            p.category,
            p.unit_price,
            p.supplier_name,
            i.hub_id,
            i.rep_dipan_id,
            i.quantity,
            i.threshold_limit,
            i.last_updated
        FROM inventory i
        JOIN products p
            ON p.product_id = i.product_id
        WHERE i.quantity IS NOT NULL
          AND i.quantity <= 0
        ORDER BY i.last_updated DESC NULLS LAST
        LIMIT :limit
        """
    )

    with _engine().connect() as conn:
        rows = conn.execute(
            query,
            {"limit": int(limit)},
        ).mappings().all()

    return [dict(row) for row in rows]