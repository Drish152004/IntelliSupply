"""Inventory REST service over current Supabase planning schema."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session
from rag.inventory import chatbot
def _get_session_factory():
    from chatbot.database import SessionLocal, engine

    return SessionLocal, engine


def _session() -> Session:
    SessionLocal, _ = _get_session_factory()
    return SessionLocal()


def _product_key(product_id: str, category: str | None) -> str:
    """
    Frontend-safe product key.

    product_id alone is not enough because the same product_id can exist
    in multiple categories.
    """
    return f"{product_id}::{category or ''}"


def _split_product_key(product_key: str) -> tuple[str, str | None]:
    if "::" in product_key:
        product_id, category = product_key.split("::", 1)
        return product_id, category or None

    return product_key, None


def _stock_status(stock: int, demand: int = 0) -> str:
    if stock <= 0:
        return "Out of Stock"

    if demand > 0 and stock < demand:
        return "Low Stock"

    if stock < 20:
        return "Low Stock"

    return "Healthy"


def list_products(
    *,
    search: str = "",
    category: str = "",
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    List inventory products using:
    - product_catalog for product metadata
    - latest planning_dataset date for current stock
    """
    search = search.strip()
    category = category.strip()

    sql = """
    WITH latest_date AS (
        SELECT MAX(date) AS latest_date
        FROM planning_dataset
    ),
    latest_inventory AS (
        SELECT
            pd.product_id,
            pd.category,
            COALESCE(SUM(pd.inventory_level), 0) AS total_stock,
            COALESCE(SUM(pd.demand), 0) AS total_demand,
            AVG(pd.price) AS avg_price
        FROM planning_dataset pd
        JOIN latest_date ld
            ON pd.date = ld.latest_date
        GROUP BY
            pd.product_id,
            pd.category
    )
    SELECT
        pc.product_id,
        pc.category,
        COALESCE(pc.product_display_name, pc.product_name, pc.product_id) AS product_name,
        COALESCE(li.total_stock, 0) AS total_stock,
        COALESCE(li.total_demand, 0) AS total_demand,
        li.avg_price AS unit_price
    FROM product_catalog pc
    LEFT JOIN latest_inventory li
        ON li.product_id = pc.product_id
       AND li.category = pc.category
    WHERE
        (
            :search = ''
            OR pc.product_id ILIKE :search_pattern
            OR pc.product_name ILIKE :search_pattern
            OR pc.product_display_name ILIKE :search_pattern
        )
        AND (
            :category = ''
            OR LOWER(:category) = 'all'
            OR pc.category ILIKE :category_pattern
        )
    ORDER BY
        product_name,
        pc.category
    LIMIT :limit
    """

    params = {
        "search": search,
        "search_pattern": f"%{search}%",
        "category": category,
        "category_pattern": category,
        "limit": limit,
    }

    with _session() as session:
        rows = session.execute(text(sql), params).mappings().all()

    products: list[dict[str, Any]] = []

    for row in rows:
        stock = int(row["total_stock"] or 0)
        demand = int(row["total_demand"] or 0)

        products.append(
            {
                "id": _product_key(row["product_id"], row["category"]),
                "product_id": row["product_id"],
                "name": row["product_name"],
                "category": row["category"],
                "unit_price": float(row["unit_price"]) if row["unit_price"] is not None else None,
                "supplier_name": None,
                "stock": stock,
                "demand": demand,
                "status": _stock_status(stock, demand),
            }
        )

    return products


def get_summary() -> dict[str, Any]:
    """
    Inventory summary using latest date from planning_dataset.
    """
    sql = """
    WITH latest_date AS (
        SELECT MAX(date) AS latest_date
        FROM planning_dataset
    ),
    latest_inventory AS (
        SELECT
            pd.product_id,
            pd.category,
            COALESCE(SUM(pd.inventory_level), 0) AS total_stock,
            COALESCE(SUM(pd.demand), 0) AS total_demand
        FROM planning_dataset pd
        JOIN latest_date ld
            ON pd.date = ld.latest_date
        GROUP BY
            pd.product_id,
            pd.category
    ),
    low_stock AS (
        SELECT
            li.product_id,
            li.category,
            li.total_stock,
            li.total_demand
        FROM latest_inventory li
        WHERE
            li.total_stock <= 0
            OR li.total_stock < li.total_demand
            OR li.total_stock < 20
    ),
    stockout AS (
        SELECT
            li.product_id,
            li.category
        FROM latest_inventory li
        WHERE li.total_stock <= 0
    )
    SELECT
        COALESCE((SELECT SUM(total_stock) FROM latest_inventory), 0) AS on_hand_units,
        COALESCE((SELECT SUM(total_demand) FROM latest_inventory), 0) AS total_demand,
        COALESCE((SELECT COUNT(*) FROM product_catalog), 0) AS product_count,
        COALESCE((SELECT COUNT(*) FROM hubs), 0) AS warehouse_count,
        COALESCE((SELECT COUNT(*) FROM low_stock), 0) AS reorder_alerts,
        COALESCE((SELECT COUNT(*) FROM stockout), 0) AS stockout_count
    """

    risk_sql = """
    WITH latest_date AS (
        SELECT MAX(date) AS latest_date
        FROM planning_dataset
    ),
    latest_inventory AS (
        SELECT
            pd.product_id,
            pd.category,
            COALESCE(SUM(pd.inventory_level), 0) AS total_stock,
            COALESCE(SUM(pd.demand), 0) AS total_demand
        FROM planning_dataset pd
        JOIN latest_date ld
            ON pd.date = ld.latest_date
        GROUP BY
            pd.product_id,
            pd.category
    )
    SELECT
        COALESCE(pc.product_display_name, pc.product_name, pc.product_id) AS product_name,
        li.category,
        li.total_stock,
        li.total_demand
    FROM latest_inventory li
    JOIN product_catalog pc
        ON pc.product_id = li.product_id
       AND pc.category = li.category
    WHERE
        li.total_stock <= 0
        OR li.total_stock < li.total_demand
        OR li.total_stock < 20
    ORDER BY
        CASE
            WHEN li.total_stock <= 0 THEN 0
            WHEN li.total_stock < li.total_demand THEN 1
            ELSE 2
        END,
        li.total_stock ASC
    LIMIT 5
    """

    with _session() as session:
        row = session.execute(text(sql)).mappings().first()
        risk_rows = session.execute(text(risk_sql)).mappings().all()

    on_hand_units = int(row["on_hand_units"] or 0)
    total_demand = int(row["total_demand"] or 0)
    product_count = int(row["product_count"] or 0)
    warehouse_count = int(row["warehouse_count"] or 0)
    reorder_alerts = int(row["reorder_alerts"] or 0)
    stockout_count = int(row["stockout_count"] or 0)

    stockout_pct = round((stockout_count / product_count) * 100, 1) if product_count else 0.0

    demand_coverage_pct = (
        round(min((on_hand_units / total_demand) * 100, 100.0), 1)
        if total_demand > 0
        else 100.0
    )

    risk_signals = []

    for item in risk_rows:
        stock = int(item["total_stock"] or 0)
        demand = int(item["total_demand"] or 0)
        product_name = item["product_name"]

        if stock <= 0:
            title = "Immediate reorder needed"
            severity = "Critical"
            description = f"{product_name} is out of stock across hubs."
        elif demand > 0 and stock < demand:
            title = "Demand exceeds stock"
            severity = "High"
            description = f"{product_name} has {stock} units, below demand of {demand}."
        else:
            title = "Low buffer stock"
            severity = "Medium"
            description = f"{product_name} has only {stock} units available."

        risk_signals.append(
            {
                "title": title,
                "description": description,
                "severity": severity,
            }
        )

    return {
        "on_hand_units": on_hand_units,
        "warehouse_count": warehouse_count,
        "product_count": product_count,
        "stockout_risk_pct": stockout_pct,
        "demand_coverage_pct": demand_coverage_pct,
        "reorder_alerts": reorder_alerts,
        "risk_signals": risk_signals,
    }


def get_forecast_trend() -> list[dict[str, Any]]:
    """
    Return trend from actual planning_dataset data.

    Uses last 7 available dates.
    """
    sql = """
    SELECT
        pd.date,
        COALESCE(SUM(pd.demand), 0) AS demand,
        COALESCE(SUM(pd.inventory_level), 0) AS inventory
    FROM planning_dataset pd
    GROUP BY pd.date
    ORDER BY pd.date DESC
    LIMIT 7
    """

    with _session() as session:
        rows = session.execute(text(sql)).mappings().all()

    trend = []

    for row in reversed(rows):
        trend.append(
            {
                "period": row["date"].strftime("%b %d") if hasattr(row["date"], "strftime") else str(row["date"]),
                "demand": int(row["demand"] or 0),
                "inventory": int(row["inventory"] or 0),
            }
        )

    return trend


def create_product(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Create product in product_catalog only.

    Stock is not created here because stock comes from planning_dataset.
    """
    product_id = payload.get("product_id") or payload.get("id") or f"PRD-{uuid.uuid4().hex[:8].upper()}"
    product_name = payload["name"].strip()
    category = payload.get("category") or "General"

    sql = """
    INSERT INTO product_catalog (
        product_id,
        category,
        product_name,
        product_display_name
    )
    VALUES (
        :product_id,
        :category,
        :product_name,
        :product_display_name
    )
    ON CONFLICT (product_id, category)
    DO UPDATE SET
        product_name = EXCLUDED.product_name,
        product_display_name = EXCLUDED.product_display_name
    RETURNING
        product_id,
        category,
        COALESCE(product_display_name, product_name, product_id) AS product_name
    """

    params = {
        "product_id": product_id,
        "category": category,
        "product_name": product_name,
        "product_display_name": payload.get("product_display_name") or product_name,
    }

    with _session() as session:
        row = session.execute(text(sql), params).mappings().first()
        session.commit()

    return {
        "id": _product_key(row["product_id"], row["category"]),
        "product_id": row["product_id"],
        "name": row["product_name"],
        "category": row["category"],
        "unit_price": None,
        "supplier_name": None,
        "stock": 0,
        "status": "Out of Stock",
    }


def update_product(product_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    """
    Update product_catalog.

    product_id param may be:
    - P0001::Electronics
    - P0001
    """
    raw_product_id, category = _split_product_key(product_id)

    name = payload.get("name")
    new_category = payload.get("category")

    select_sql = """
    SELECT
        pc.product_id,
        pc.category,
        COALESCE(pc.product_display_name, pc.product_name, pc.product_id) AS product_name
    FROM product_catalog pc
    WHERE
        pc.product_id = :product_id
        AND (:category IS NULL OR pc.category = :category)
    LIMIT 1
    """

    update_sql = """
    UPDATE product_catalog
    SET
        product_name = COALESCE(:product_name, product_name),
        product_display_name = COALESCE(:product_display_name, product_display_name),
        category = COALESCE(:new_category, category)
    WHERE
        product_id = :product_id
        AND (:category IS NULL OR category = :category)
    RETURNING
        product_id,
        category,
        COALESCE(product_display_name, product_name, product_id) AS product_name
    """

    stock_sql = """
    WITH latest_date AS (
        SELECT MAX(date) AS latest_date
        FROM planning_dataset
    )
    SELECT
        COALESCE(SUM(inventory_level), 0) AS total_stock,
        COALESCE(SUM(demand), 0) AS total_demand,
        AVG(price) AS unit_price
    FROM planning_dataset pd
    JOIN latest_date ld
        ON pd.date = ld.latest_date
    WHERE
        pd.product_id = :product_id
        AND pd.category = :category
    """

    with _session() as session:
        existing = session.execute(
            text(select_sql),
            {"product_id": raw_product_id, "category": category},
        ).mappings().first()

        if not existing:
            return None

        row = session.execute(
            text(update_sql),
            {
                "product_id": raw_product_id,
                "category": category,
                "product_name": name.strip() if isinstance(name, str) and name.strip() else None,
                "product_display_name": name.strip() if isinstance(name, str) and name.strip() else None,
                "new_category": new_category.strip() if isinstance(new_category, str) and new_category.strip() else None,
            },
        ).mappings().first()

        session.commit()

        stock_row = session.execute(
            text(stock_sql),
            {
                "product_id": row["product_id"],
                "category": row["category"],
            },
        ).mappings().first()

    stock = int(stock_row["total_stock"] or 0)
    demand = int(stock_row["total_demand"] or 0)

    return {
        "id": _product_key(row["product_id"], row["category"]),
        "product_id": row["product_id"],
        "name": row["product_name"],
        "category": row["category"],
        "unit_price": float(stock_row["unit_price"]) if stock_row["unit_price"] is not None else None,
        "supplier_name": None,
        "stock": stock,
        "demand": demand,
        "status": _stock_status(stock, demand),
    }


def delete_product(product_id: str) -> bool:
    """
    Delete product from product_catalog and planning_dataset.

    product_id param may be:
    - P0001::Electronics
    - P0001
    """
    raw_product_id, category = _split_product_key(product_id)

    delete_planning_sql = """
    DELETE FROM planning_dataset
    WHERE
        product_id = :product_id
        AND (:category IS NULL OR category = :category)
    """

    delete_catalog_sql = """
    DELETE FROM product_catalog
    WHERE
        product_id = :product_id
        AND (:category IS NULL OR category = :category)
    RETURNING product_id
    """

    with _session() as session:
        session.execute(
            text(delete_planning_sql),
            {
                "product_id": raw_product_id,
                "category": category,
            },
        )

        row = session.execute(
            text(delete_catalog_sql),
            {
                "product_id": raw_product_id,
                "category": category,
            },
        ).first()

        session.commit()

    return row is not None


def inventory_db_available() -> bool:
    try:
        _, engine = _get_session_factory()

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        return True
    except Exception:
        return False
