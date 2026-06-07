"""JWT authentication dependencies for the unified API gateway."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

ALLOWED_ROLES = frozenset(
    {"admin", "courier", "inventory_manager", "logistics_manager"}
)

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class TokenUser:
    id: str
    name: str
    email: str
    role: str
    role_id: int | None = None
    courier_id: str | None = None


def _jwt_secret() -> str:
    return os.getenv("JWT_SECRET") or os.getenv("FASTAPI_SECRET_KEY", "dev-secret-change-this")


def _jwt_expire_minutes() -> int:
    return int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))


def create_access_token(user: dict) -> str:
    """Issue a signed JWT for an authenticated user dict."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "name": user.get("name", ""),
        "role": user["role"],
        "role_id": user.get("role_id"),
        "courier_id": user.get("courier_id"),
        "iat": now,
        "exp": now + timedelta(minutes=_jwt_expire_minutes()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def decode_access_token(token: str) -> TokenUser:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    role = str(payload.get("role") or "").strip().lower()
    if role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid role in token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub = payload.get("sub")
    email = payload.get("email")
    if not sub or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    courier_id = payload.get("courier_id")
    return TokenUser(
        id=str(sub),
        name=str(payload.get("name") or ""),
        email=str(email),
        role=role,
        role_id=payload.get("role_id"),
        courier_id=str(courier_id).strip() if courier_id else None,
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> TokenUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_access_token(credentials.credentials)


def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> TokenUser | None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    try:
        return decode_access_token(credentials.credentials)
    except HTTPException:
        return None


def require_roles(*roles: str) -> Callable[..., TokenUser]:
    allowed = frozenset(roles)

    def _dependency(user: Annotated[TokenUser, Depends(get_current_user)]) -> TokenUser:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not permitted for this resource.",
            )
        return user

    return _dependency


def user_to_authenticated_payload(user: TokenUser) -> dict:
    """Build orchestrator identity from a validated JWT user."""
    payload: dict = {"role": user.role}
    if user.courier_id:
        payload["courier_id"] = user.courier_id
    return payload
