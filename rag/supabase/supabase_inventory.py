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
        row = conn.execute(query, {"product_id": str(product_id)}).mappings().first()
        return dict(row) if row else None

def get_inventory_by_hub(hub_id: int) -> list[dict[str, Any]]:
    query = text(
        """
        SELECT *
        FROM inventory
        WHERE hub_id = :hub_id
        ORDER BY product_id
        """
    )
    with _engine().connect() as conn:
        rows = conn.execute(query, {"hub_id": int(hub_id)}).mappings().all()
        return [dict(row) for row in rows]

def get_low_stock_items(threshold: int = 10) -> list[dict[str, Any]]:
    query = text(
        """
        SELECT *
        FROM inventory
        WHERE quantity <= :threshold
        ORDER BY quantity ASC
        """
    )
    with _engine().connect() as conn:
        rows = conn.execute(query, {"threshold": int(threshold)}).mappings().all()
        return [dict(row) for row in rows]