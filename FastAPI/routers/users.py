"""User management API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from aura_graphdb.aura_auth import list_all_users
from dependencies.auth import TokenUser, require_roles

router = APIRouter(prefix="/api", tags=["users"])

AdminUser = Annotated[TokenUser, Depends(require_roles("admin"))]


@router.get("/users")
def list_users(current_user: AdminUser, limit: int = 100):
    del current_user
    try:
        rows = list_all_users(limit=limit)
    except (ConnectionError, ServiceUnavailable, Neo4jError, OSError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    users = []
    for row in rows:
        users.append(
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "email": row.get("email"),
                "role": row.get("role"),
                "account_type": row.get("account_type"),
                "is_active": row.get("is_active", True),
            }
        )
    return {"success": True, "users": users, "count": len(users)}
