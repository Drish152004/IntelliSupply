"""Inventory REST service over Postgres."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session


def _get_session_factory():
    from chatbot.database import SessionLocal, engine

    return SessionLocal, engine


def _session() -> Session:
    SessionLocal, _ = _get_session_factory()
    return SessionLocal()


def list_products(*, search: str = "", category: str = "", limit: int = 100) -> list[dict[str, Any]]:
    from chatbot.models import Inventory, Product

    with _session() as session:
        query = session.query(
            Product.product_id,
            Product.product_name,
            Product.category,
            Product.unit_price,
            Product.supplier_name,
            func.coalesce(func.sum(Inventory.quantity), 0).label("total_stock"),
        ).outerjoin(Inventory, Inventory.product_id == Product.product_id)

        if search.strip():
            pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Product.product_name.ilike(pattern),
                    Product.product_id.ilike(pattern),
                )
            )
        if category.strip() and category.strip().lower() != "all":
            query = query.filter(Product.category.ilike(category.strip()))

        query = query.group_by(
            Product.product_id,
            Product.product_name,
            Product.category,
            Product.unit_price,
            Product.supplier_name,
        ).order_by(Product.product_name).limit(limit)

        rows = []
        for row in query.all():
            stock = int(row.total_stock or 0)
            rows.append(
                {
                    "id": row.product_id,
                    "name": row.product_name,
                    "category": row.category,
                    "unit_price": row.unit_price,
                    "supplier_name": row.supplier_name,
                    "stock": stock,
                    "status": _stock_status(stock),
                }
            )
        return rows


def _stock_status(stock: int) -> str:
    if stock <= 0:
        return "Out of Stock"
    if stock < 20:
        return "Low Stock"
    return "Healthy"


def get_summary() -> dict[str, Any]:
    from chatbot.models import Inventory, Product, Warehouse

    with _session() as session:
        total_units = session.query(func.coalesce(func.sum(Inventory.quantity), 0)).scalar() or 0
        product_count = session.query(func.count(Product.product_id)).scalar() or 0
        warehouse_count = session.query(func.count(Warehouse.hub_id)).scalar() or 0

        low_stock_rows = (
            session.query(Product.product_name, func.coalesce(func.sum(Inventory.quantity), 0))
            .outerjoin(Inventory, Inventory.product_id == Product.product_id)
            .group_by(Product.product_id, Product.product_name)
            .having(func.coalesce(func.sum(Inventory.quantity), 0) < 20)
            .all()
        )
        reorder_alerts = len(low_stock_rows)

        stockout_rows = (
            session.query(Product.product_name)
            .outerjoin(Inventory, Inventory.product_id == Product.product_id)
            .group_by(Product.product_id, Product.product_name)
            .having(func.coalesce(func.sum(Inventory.quantity), 0) <= 0)
            .all()
        )
        stockout_pct = round((len(stockout_rows) / product_count) * 100, 1) if product_count else 0.0

        return {
            "on_hand_units": int(total_units),
            "warehouse_count": int(warehouse_count),
            "product_count": int(product_count),
            "stockout_risk_pct": stockout_pct,
            "demand_coverage_pct": max(0.0, min(100.0, 100.0 - stockout_pct)),
            "reorder_alerts": reorder_alerts,
            "risk_signals": [
                {
                    "title": "Low buffer stock" if qty > 0 else "Immediate reorder needed",
                    "description": f"{name} has {int(qty)} units across hubs.",
                    "severity": "High" if qty > 0 else "Critical",
                }
                for name, qty in low_stock_rows[:5]
            ],
        }


def get_forecast_trend() -> list[dict[str, Any]]:
    """Return a simple 7-day trend derived from current inventory totals."""
    summary = get_summary()
    base_inventory = max(summary["on_hand_units"], 1)
    base_demand = max(int(base_inventory * 0.08), 50)
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    trend = []
    inventory = float(base_inventory)
    for index, day in enumerate(days):
        demand = base_demand + index * 35
        inventory = max(inventory - demand * 0.45, summary["on_hand_units"] * 0.25)
        trend.append(
            {
                "period": day,
                "demand": demand,
                "inventory": int(inventory),
            }
        )
    return trend


def create_product(payload: dict[str, Any]) -> dict[str, Any]:
    from chatbot.models import Product

    product_id = payload.get("id") or f"PRD-{uuid.uuid4().hex[:8].upper()}"
    with _session() as session:
        product = Product(
            product_id=product_id,
            product_name=payload["name"].strip(),
            category=payload.get("category", "General"),
            unit_price=float(payload.get("unit_price") or 0),
            supplier_name=payload.get("supplier_name"),
        )
        session.add(product)
        session.commit()
        return {
            "id": product.product_id,
            "name": product.product_name,
            "category": product.category,
            "unit_price": product.unit_price,
            "supplier_name": product.supplier_name,
            "stock": 0,
            "status": "Out of Stock",
        }


def update_product(product_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    from chatbot.models import Inventory, Product

    with _session() as session:
        product = session.get(Product, product_id)
        if not product:
            return None
        if payload.get("name"):
            product.product_name = payload["name"].strip()
        if payload.get("category"):
            product.category = payload["category"].strip()
        if payload.get("unit_price") is not None:
            product.unit_price = float(payload["unit_price"])
        if payload.get("supplier_name") is not None:
            product.supplier_name = payload["supplier_name"]
        session.commit()
        stock = (
            session.query(func.coalesce(func.sum(Inventory.quantity), 0))
            .filter(Inventory.product_id == product_id)
            .scalar()
            or 0
        )
        return {
            "id": product.product_id,
            "name": product.product_name,
            "category": product.category,
            "unit_price": product.unit_price,
            "supplier_name": product.supplier_name,
            "stock": int(stock),
            "status": _stock_status(int(stock)),
        }


def delete_product(product_id: str) -> bool:
    from chatbot.models import Inventory, Product

    with _session() as session:
        product = session.get(Product, product_id)
        if not product:
            return False
        session.query(Inventory).filter(Inventory.product_id == product_id).delete()
        session.delete(product)
        session.commit()
        return True


def inventory_db_available() -> bool:
    try:
        _, engine = _get_session_factory()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
