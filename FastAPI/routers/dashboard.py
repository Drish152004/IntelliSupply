"""Dashboard summary API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from dependencies.auth import TokenUser, require_roles
from services import dashboard as dashboard_svc

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

DashboardUser = Annotated[
    TokenUser,
    Depends(require_roles("admin", "logistics_manager", "inventory_manager")),
]

LogisticsDashboardUser = Annotated[
    TokenUser,
    Depends(require_roles("admin", "logistics_manager", "courier")),
]


@router.get("/summary")
def dashboard_summary(current_user: DashboardUser):
    del current_user
    return {"success": True, "summary": dashboard_svc.get_dashboard_summary()}


@router.get("/logistics-kpis")
def logistics_kpis(
    current_user: LogisticsDashboardUser,
    delivery_day: str | None = Query(default=None, description="YYYY-MM-DD"),
):
    del current_user
    return {"success": True, "kpis": dashboard_svc.get_logistics_kpis(delivery_day)}
