"""Operational notifications API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from dependencies.auth import TokenUser, get_current_user
from services import notifications as notifications_svc

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
def list_notifications(
    current_user: Annotated[TokenUser, Depends(get_current_user)],
    limit: int = 20,
):
    items = notifications_svc.list_notifications(role=current_user.role, limit=limit)
    return {"success": True, "notifications": items, "count": len(items)}
