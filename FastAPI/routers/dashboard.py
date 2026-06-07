"""Dashboard summary API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from dependencies.auth import TokenUser, require_roles
from services import dashboard as dashboard_svc

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

DashboardUser = Annotated[
    TokenUser,
    Depends(require_roles("admin", "logistics_manager", "inventory_manager")),
]


@router.get("/summary")
def dashboard_summary(current_user: DashboardUser):
    del current_user
    return {"success": True, "summary": dashboard_svc.get_dashboard_summary()}
