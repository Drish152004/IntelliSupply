"""Inventory REST API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from dependencies.auth import TokenUser, require_roles
from services import inventory as inventory_svc

router = APIRouter(prefix="/inventory", tags=["inventory"])

InventoryUser = Annotated[
    TokenUser,
    Depends(require_roles("admin", "inventory_manager")),
]


class ProductCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    category: str = Field(default="General")
    unit_price: float = Field(default=0, ge=0)
    supplier_name: str | None = None


class ProductUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    category: str | None = None
    unit_price: float | None = Field(default=None, ge=0)
    supplier_name: str | None = None


def _ensure_db():
    if not inventory_svc.inventory_db_available():
        raise HTTPException(status_code=503, detail="Inventory database unavailable.")


@router.get("/products")
def list_products(
    current_user: InventoryUser,
    search: str = "",
    category: str = "",
    limit: int = 100,
):
    del current_user
    _ensure_db()
    products = inventory_svc.list_products(search=search, category=category, limit=limit)
    return {"success": True, "products": products, "count": len(products)}


@router.post("/products", status_code=201)
def create_product(body: ProductCreateRequest, current_user: InventoryUser):
    del current_user
    _ensure_db()
    product = inventory_svc.create_product(body.model_dump())
    return {"success": True, "product": product}


@router.patch("/products/{product_id}")
def update_product(product_id: str, body: ProductUpdateRequest, current_user: InventoryUser):
    del current_user
    _ensure_db()
    updated = inventory_svc.update_product(product_id, body.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Product not found.")
    return {"success": True, "product": updated}


@router.delete("/products/{product_id}")
def delete_product(product_id: str, current_user: InventoryUser):
    del current_user
    _ensure_db()
    if not inventory_svc.delete_product(product_id):
        raise HTTPException(status_code=404, detail="Product not found.")
    return {"success": True, "message": "Product deleted."}


@router.get("/summary")
def inventory_summary(current_user: InventoryUser):
    del current_user
    _ensure_db()
    return {"success": True, "summary": inventory_svc.get_summary()}


@router.get("/forecast-trend")
def inventory_forecast_trend(current_user: InventoryUser):
    del current_user
    _ensure_db()
    return {"success": True, "trend": inventory_svc.get_forecast_trend()}
