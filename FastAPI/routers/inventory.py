"""Inventory REST API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from dependencies.auth import TokenUser, require_roles
from services import inventory as inventory_svc


router = APIRouter(prefix="/inventory", tags=["inventory"])

InventoryUser = Annotated[
    TokenUser,
    Depends(require_roles("admin", "inventory_manager")),
]


class ProductCreateRequest(BaseModel):
    product_id: str | None = None
    name: str = Field(..., min_length=1)
    category: str = Field(default="General")
    unit_price: float | None = Field(default=None, ge=0)
    supplier_name: str | None = None
    product_display_name: str | None = None


class ProductUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    category: str | None = None
    unit_price: float | None = Field(default=None, ge=0)
    supplier_name: str | None = None
    product_display_name: str | None = None


class StockEntryCreateRequest(BaseModel):
    category: str = Field(..., min_length=1)
    product_id: str = Field(..., min_length=1)
    city_id: int
    hub_id: int

    inventory_level: int = Field(..., ge=0)
    units_ordered: int | None = Field(default=0, ge=0)
    price: float | None = Field(default=None, ge=0)
    demand: int | None = Field(default=0, ge=0)
    discount: float | None = Field(default=0, ge=0)

    units_sold: int | None = Field(default=0, ge=0)
    weather_condition: str | None = None
    promotion: int | None = Field(default=0, ge=0)
    competitor_pricing: float | None = Field(default=None, ge=0)
    seasonality: str | None = None
    epidemic: int | None = Field(default=0, ge=0)


def _ensure_db():
    if not inventory_svc.inventory_db_available():
        raise HTTPException(
            status_code=503,
            detail=(
                "Inventory database unavailable. Check Supabase/Postgres connection "
                "and required tables: product_catalog, planning_dataset, hubs, cities."
            ),
        )


@router.get("/products")
def list_products(
    current_user: InventoryUser,
    search: str = Query(default=""),
    category: str = Query(default=""),
    limit: int = Query(default=100, ge=1, le=500),
):
    del current_user
    _ensure_db()

    products = inventory_svc.list_products(
        search=search,
        category=category,
        limit=limit,
    )

    return {
        "success": True,
        "products": products,
        "count": len(products),
    }


@router.get("/categories")
def list_categories(current_user: InventoryUser):
    del current_user
    _ensure_db()

    categories = inventory_svc.list_categories()

    return {
        "success": True,
        "categories": categories,
        "count": len(categories),
    }


@router.get("/products/by-category")
def list_products_by_category(
    current_user: InventoryUser,
    category: str = Query(..., min_length=1),
    limit: int = Query(default=200, ge=1, le=500),
):
    del current_user
    _ensure_db()

    products = inventory_svc.list_products_by_category(
        category=category,
        limit=limit,
    )

    return {
        "success": True,
        "products": products,
        "count": len(products),
    }


@router.get("/cities")
def list_cities(current_user: InventoryUser):
    del current_user
    _ensure_db()

    cities = inventory_svc.list_cities()

    return {
        "success": True,
        "cities": cities,
        "count": len(cities),
    }


@router.get("/hubs")
def list_hubs(
    current_user: InventoryUser,
    city_id: int = Query(...),
):
    del current_user
    _ensure_db()

    hubs = inventory_svc.list_hubs_by_city(city_id=city_id)

    return {
        "success": True,
        "hubs": hubs,
        "count": len(hubs),
    }


@router.post("/stock-entry", status_code=201)
def create_stock_entry(
    body: StockEntryCreateRequest,
    current_user: InventoryUser,
):
    del current_user
    _ensure_db()

    try:
        product = inventory_svc.create_stock_entry(body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return {
        "success": True,
        "product": product,
    }


@router.post("/products", status_code=201)
def create_product(
    body: ProductCreateRequest,
    current_user: InventoryUser,
):
    del current_user
    _ensure_db()

    product = inventory_svc.create_product(body.model_dump())

    return {
        "success": True,
        "product": product,
    }


@router.patch("/products/{product_id}")
def update_product(
    product_id: str,
    body: ProductUpdateRequest,
    current_user: InventoryUser,
):
    del current_user
    _ensure_db()

    updated = inventory_svc.update_product(
        product_id,
        body.model_dump(exclude_unset=True),
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Product not found.")

    return {
        "success": True,
        "product": updated,
    }


@router.delete("/products/{product_id}")
def delete_product(
    product_id: str,
    current_user: InventoryUser,
):
    del current_user
    _ensure_db()

    deleted = inventory_svc.delete_product(product_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found.")

    return {
        "success": True,
        "message": "Product deleted.",
    }


@router.get("/summary")
def inventory_summary(current_user: InventoryUser):
    del current_user
    _ensure_db()

    return {
        "success": True,
        "summary": inventory_svc.get_summary(),
    }


@router.get("/forecast-trend")
def inventory_forecast_trend(current_user: InventoryUser):
    del current_user
    _ensure_db()

    return {
        "success": True,
        "trend": inventory_svc.get_forecast_trend(),
    }