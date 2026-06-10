"""Operational notifications API routes."""

from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from dependencies.auth import TokenUser, get_current_user
from services import notifications as notifications_svc

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

@router.get("")
def list_notifications(
    current_user: Annotated[TokenUser, Depends(get_current_user)],
    limit: int = 20,
):
    items = notifications_svc.list_notifications(
        user_id=current_user.id,
        role=current_user.role,
        limit=limit,
    )

    return {
        "success": True,
        "notifications": items,
        "count": len(items),
    }

@router.get("/unread-count")
def get_unread_count(
    current_user: Annotated[TokenUser, Depends(get_current_user)],
):
    count = notifications_svc.unread_count(
        user_id=current_user.id,
        role=current_user.role,
    )

    return {
        "success": True,
        "unread_count": count,
    }

@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: str,
    current_user: Annotated[TokenUser, Depends(get_current_user)],
):
    notification = notifications_svc.mark_as_read(notification_id)

    if not notification:
        raise HTTPException(
            status_code=404,
            detail="Notification not found.",
        )

    return {
        "success": True,
        "notification": notification,
    }

@router.patch("/read-all")
def mark_all_notifications_read(
    current_user: Annotated[TokenUser, Depends(get_current_user)],
):
    updated_count = notifications_svc.mark_all_as_read(
        user_id=current_user.id,
        role=current_user.role,
    )

    return {
        "success": True,
        "updated_count": updated_count,
    }