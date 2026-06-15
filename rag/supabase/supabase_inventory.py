from typing import Any
from sqlalchemy import text
from rag.supabase.supabase_connection import get_supabase_engine

def _engine():
    return get_supabase_engine()

def list_products(limit: int = 100) -> list[dict[str, Any]]:
    """
    List products from product_catalog.
    Product identity is product_id + category.
    """
    query = text(
        """
        SELECT
            pc.id,
            pc.product_id,
            pc.category,
            pc.product_name,
            pc.product_display_name,
            pc.created_at
        FROM product_catalog pc
        ORDER BY pc.category, pc.product_name
        LIMIT :limit
        """
    )

    with _engine().connect() as conn:
        rows = conn.execute(query, {"limit": int(limit)}).mappings().all()

    return [dict(row) for row in rows]

def get_product_by_id(product_id: str) -> list[dict[str, Any]]:
    """
    Return all catalog entries for a product_id.
    Same product_id can exist in multiple categories.
    """
    query = text(
        """
        SELECT
            pc.id,
            pc.product_id,
            pc.category,
            pc.product_name,
            pc.product_display_name,
            pc.created_at
        FROM product_catalog pc
        WHERE pc.product_id::text = :product_id
        ORDER BY pc.category, pc.product_name
        """
    )

    with _engine().connect() as conn:
        rows = conn.execute(
            query,
            {"product_id": str(product_id)},
        ).mappings().all()

    return [dict(row) for row in rows]

def get_product_by_id_and_category(
    product_id: str,
    category: str,
) -> dict[str, Any] | None:
    """
    Return one exact product-category catalog record.
    """
    query = text(
        """
        SELECT
            pc.id,
            pc.product_id,
            pc.category,
            pc.product_name,
            pc.product_display_name,
            pc.created_at
        FROM product_catalog pc
        WHERE pc.product_id::text = :product_id
          AND pc.category ILIKE :category
        LIMIT 1
        """
    )

    with _engine().connect() as conn:
        row = conn.execute(
            query,
            {
                "product_id": str(product_id),
                "category": str(category),
            },
        ).mappings().first()

    return dict(row) if row else None

def get_inventory_by_hub(
    hub_id: str,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Get latest available inventory records for a hub.
    Uses planning_dataset.inventory_level as stock.
    """
    query = text(
        """
        WITH latest_date AS (
            SELECT MAX(date) AS max_date
            FROM planning_dataset
            WHERE hub_id::text = :hub_id
        )
        SELECT
            pd.id,
            pd.date,
            pd.hub_id,
            h.hub_name,
            h.hub_type,
            h.city_id,
            pd.product_id,
            pd.category,
            pc.product_name,
            pc.product_display_name,
            pd.inventory_level,
            pd.units_sold,
            pd.units_ordered,
            pd.demand,
            pd.price,
            pd.discount,
            pd.weather_condition,
            pd.promotion,
            pd.competitor_pricing,
            pd.seasonality,
            pd.epidemic
        FROM planning_dataset pd
        JOIN latest_date ld
            ON pd.date = ld.max_date
        JOIN product_catalog pc
            ON pc.product_id = pd.product_id
           AND pc.category = pd.category
        JOIN hubs h
            ON h.hub_id = pd.hub_id
        WHERE pd.hub_id::text = :hub_id
        ORDER BY pd.category, pc.product_name
        LIMIT :limit
        """
    )

    with _engine().connect() as conn:
        rows = conn.execute(
            query,
            {
                "hub_id": str(hub_id),
                "limit": int(limit),
            },
        ).mappings().all()

    return [dict(row) for row in rows]

def get_inventory_by_product(
    product_id: str,
    category: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Get latest inventory for a product across hubs.
    If category is provided, filters exact product-category.
    """
    if category:
        category_filter = "AND pd.category ILIKE :category"
        params = {
            "product_id": str(product_id),
            "category": str(category),
            "limit": int(limit),
        }
    else:
        category_filter = ""
        params = {
            "product_id": str(product_id),
            "limit": int(limit),
        }

    query = text(
        f"""
        WITH latest_date AS (
            SELECT MAX(date) AS max_date
            FROM planning_dataset
        )
        SELECT
            pd.id,
            pd.date,
            pd.hub_id,
            h.hub_name,
            h.hub_type,
            h.city_id,
            pd.product_id,
            pd.category,
            pc.product_name,
            pc.product_display_name,
            pd.inventory_level,
            pd.units_sold,
            pd.units_ordered,
            pd.demand,
            pd.price,
            pd.discount
        FROM planning_dataset pd
        JOIN latest_date ld
            ON pd.date = ld.max_date
        JOIN product_catalog pc
            ON pc.product_id = pd.product_id
           AND pc.category = pd.category
        JOIN hubs h
            ON h.hub_id = pd.hub_id
        WHERE pd.product_id::text = :product_id
        {category_filter}
        ORDER BY pd.inventory_level DESC NULLS LAST
        LIMIT :limit
        """
    )

    with _engine().connect() as conn:
        rows = conn.execute(query, params).mappings().all()

    return [dict(row) for row in rows]

def get_low_stock_items(threshold: int = 10, limit: int = 100) -> list[dict[str, Any]]:
    """
    Get latest records where inventory_level is less than or equal to a fixed threshold.
    """
    query = text(
        """
        WITH latest_date AS (
            SELECT MAX(date) AS max_date
            FROM planning_dataset
        )
        SELECT
            pd.id,
            pd.date,
            pd.hub_id,
            h.hub_name,
            h.hub_type,
            h.city_id,
            pd.product_id,
            pd.category,
            pc.product_name,
            pc.product_display_name,
            pd.inventory_level,
            pd.units_sold,
            pd.units_ordered,
            pd.demand,
            pd.price,
            pd.discount
        FROM planning_dataset pd
        JOIN latest_date ld
            ON pd.date = ld.max_date
        JOIN product_catalog pc
            ON pc.product_id = pd.product_id
           AND pc.category = pd.category
        JOIN hubs h
            ON h.hub_id = pd.hub_id
        WHERE pd.inventory_level IS NOT NULL
          AND pd.inventory_level <= :threshold
        ORDER BY pd.inventory_level ASC NULLS LAST
        LIMIT :limit
        """
    )

    with _engine().connect() as conn:
        rows = conn.execute(
            query,
            {
                "threshold": int(threshold),
                "limit": int(limit),
            },
        ).mappings().all()

    return [dict(row) for row in rows]

def get_low_stock_inventory(limit: int = 100) -> list[dict[str, Any]]:
    """
    Get latest records where inventory_level is lower than demand.
    This replaces old quantity <= threshold_limit logic.
    """
    query = text(
        """
        WITH latest_date AS (
            SELECT MAX(date) AS max_date
            FROM planning_dataset
        )
        SELECT
            pd.id,
            pd.date,
            pd.hub_id,
            h.hub_name,
            h.hub_type,
            h.city_id,
            pd.product_id,
            pd.category,
            pc.product_name,
            pc.product_display_name,
            pd.inventory_level,
            pd.demand,
            pd.units_sold,
            pd.units_ordered,
            GREATEST(pd.demand - pd.inventory_level, 0) AS inventory_gap,
            pd.price,
            pd.discount
        FROM planning_dataset pd
        JOIN latest_date ld
            ON pd.date = ld.max_date
        JOIN product_catalog pc
            ON pc.product_id = pd.product_id
           AND pc.category = pd.category
        JOIN hubs h
            ON h.hub_id = pd.hub_id
        WHERE pd.inventory_level IS NOT NULL
          AND pd.demand IS NOT NULL
          AND pd.inventory_level < pd.demand
        ORDER BY inventory_gap DESC, pd.inventory_level ASC
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
    """
    Get latest records where stock is zero or demand was not fulfilled.
    """
    query = text(
        """
        WITH latest_date AS (
            SELECT MAX(date) AS max_date
            FROM planning_dataset
        )
        SELECT
            pd.id,
            pd.date,
            pd.hub_id,
            h.hub_name,
            h.hub_type,
            h.city_id,
            pd.product_id,
            pd.category,
            pc.product_name,
            pc.product_display_name,
            pd.inventory_level,
            pd.demand,
            pd.units_sold,
            pd.units_ordered,
            GREATEST(pd.demand - pd.units_sold, 0) AS lost_demand,
            pd.price,
            pd.discount
        FROM planning_dataset pd
        JOIN latest_date ld
            ON pd.date = ld.max_date
        JOIN product_catalog pc
            ON pc.product_id = pd.product_id
           AND pc.category = pd.category
        JOIN hubs h
            ON h.hub_id = pd.hub_id
        WHERE (
            pd.inventory_level IS NOT NULL
            AND pd.inventory_level <= 0
        )
        OR (
            pd.demand IS NOT NULL
            AND pd.units_sold IS NOT NULL
            AND pd.demand > pd.units_sold
        )
        ORDER BY lost_demand DESC, pd.inventory_level ASC NULLS LAST
        LIMIT :limit
        """
    )

    with _engine().connect() as conn:
        rows = conn.execute(
            query,
            {"limit": int(limit)},
        ).mappings().all()

    return [dict(row) for row in rows]

def search_products_by_name(
    product_name: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Search product catalog by product_name or product_display_name.
    """
    query = text(
        """
        SELECT
            pc.id,
            pc.product_id,
            pc.category,
            pc.product_name,
            pc.product_display_name,
            pc.created_at
        FROM product_catalog pc
        WHERE pc.product_name ILIKE :pattern
           OR pc.product_display_name ILIKE :pattern
        ORDER BY pc.category, pc.product_name
        LIMIT :limit
        """
    )

    with _engine().connect() as conn:
        rows = conn.execute(
            query,
            {
                "pattern": f"%{product_name}%",
                "limit": int(limit),
            },
        ).mappings().all()

    return [dict(row) for row in rows]

def list_hubs(limit: int = 100) -> list[dict[str, Any]]:
    """
    List hubs.
    """
    query = text(
        """
        SELECT
            h.hub_id,
            h.hub_name,
            h.city_id,
            h.poi_lat,
            h.poi_lng,
            h.lat,
            h.lng,
            h.representative_aoi_id,
            h.representative_typecode,
            h.hub_type,
            h.created_at
        FROM hubs h
        ORDER BY h.hub_id
        LIMIT :limit
        """
    )

    with _engine().connect() as conn:
        rows = conn.execute(query, {"limit": int(limit)}).mappings().all()

    return [dict(row) for row in rows]
