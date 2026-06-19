"""
JWT + OAuth authentication API for IntelliSupply (SPA-friendly).

- Stateless JWT (access + refresh)
- API-based Google OAuth (no sessions)
- Compatible with React + Agentic AI
"""

from __future__ import annotations

import os
from fastapi import APIRouter, Depends, Request, Cookie, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from security import rate_limit

from dependencies.auth import (
    TokenUser,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_current_user,
    get_current_user_optional,
)

from rag.aura_graphdb.aura_auth import (
    count_profiles,
    get_user_by_email,
    login_user_with_password,
    register_user_with_password,
    update_user_profile,
)

from rag.aura_graphdb.aura_courier import get_courier_by_email

# Google OAuth
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests


router = APIRouter(tags=["auth"])

# ✅ REQUIRED FOR SECURITY (no behavioral change, just validation)
VALID_ROLES = ["admin", "logistics_manager", "inventory_manager", "courier"]


# ─────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────

class ProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _serialize_user(user: dict, *, courier_id: str | None = None) -> dict:
    payload = {
        "id": user.get("id") or user.get("courier_id"),
        "name": user.get("name"),
        "email": user.get("email"),
        "role_id": user.get("role_id"),
        "role": user.get("role"),
    }
    if courier_id:
        payload["courier_id"] = courier_id
    return payload


def _build_auth_response(user: dict, courier_id: str | None = None):
    serialized = _serialize_user(user, courier_id=courier_id)

    token_payload = {**serialized}
    if courier_id:
        token_payload["courier_id"] = courier_id

    access_token = create_access_token(token_payload)
    refresh_token = create_refresh_token(token_payload)

    response = JSONResponse({
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "user": serialized,
    })

    is_prod = os.getenv("ENV", "development") == "production"

    # ✅ ✅ FIXED COOKIE (DO NOT CHANGE ANYTHING ELSE)
    response.set_cookie(
        key="intellisupply_refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_prod,        # ✅ correct for prod/dev
        samesite="lax",        # ✅ FIX (was "none" ❌)
        path="/",
        max_age=7 * 24 * 3600,
    )

    return response


def _try_login(email: str, password: str) -> dict | None:
    result = login_user_with_password(email=email, password=password)

    if not result["success"]:
        return None

    user = result["user"]

    courier_id = None
    if user.get("role") == "courier":
        courier = get_courier_by_email(email)
        if courier:
            courier_id = courier.get("courier_id")

    return {"user": user, "courier_id": courier_id}


# ─────────────────────────────────────────────
# Auth Endpoints
# ─────────────────────────────────────────────

@router.post("/api/login", dependencies=[Depends(rate_limit(5, 60))])
async def api_login(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"success": False, "message": "Invalid request body."}, status_code=400)

    email = (body.get("email") or "").strip()
    password = (body.get("password") or "").strip()

    if not email or not password:
        return JSONResponse({"success": False, "message": "Email and password required."}, status_code=400)

    auth_result = _try_login(email, password)

    if not auth_result:
        return JSONResponse({"success": False, "message": "Invalid credentials."}, status_code=401)

    return _build_auth_response(**auth_result)


@router.post("/api/register", dependencies=[Depends(rate_limit(5, 60))])
async def api_register(
    request: Request,
    current_user: TokenUser | None = Depends(get_current_user_optional),
):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"success": False, "message": "Invalid body."}, status_code=400)

    name = (body.get("name") or "").strip()
    email = (body.get("email") or "").strip()
    password = (body.get("password") or "").strip()
    role = (body.get("role") or "courier").strip()

    if not name or not email or not password:
        return JSONResponse({"success": False, "message": "Missing fields."}, status_code=400)

    if count_profiles() > 0:
        if current_user is None or current_user.role != "admin":
            return JSONResponse({"success": False, "message": "Admin only."}, status_code=403)

    # ✅ SAFE ROLE VALIDATION (no feature change)
    selected_role = role if role in VALID_ROLES else None
    if not selected_role:
        return JSONResponse({"success": False, "message": "Invalid role selection."}, status_code=400)

    result = register_user_with_password(
        name=name,
        email=email,
        password=password,
        selected_role=selected_role,
    )

    if not result["success"]:
        return JSONResponse({"success": False, "message": result["message"]}, status_code=422)

    return _build_auth_response(result["user"]), 201


# ─────────────────────────────────────────────
# Google OAuth
# ─────────────────────────────────────────────

@router.post("/api/google-login", dependencies=[Depends(rate_limit(5, 60))])
async def google_login(request: Request):
    try:
        body = await request.json()
        token = body.get("id_token")
        requested_role = (body.get("role") or "").strip()
    except Exception:
        return JSONResponse({"success": False, "message": "Invalid request."}, status_code=400)

    if not token:
        return JSONResponse({"success": False, "message": "Missing Google token."}, status_code=400)

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            os.getenv("GOOGLE_CLIENT_ID"),
        )
    except Exception as e:
        print("Google OAuth error:", str(e))
        return JSONResponse({"success": False, "message": "Invalid Google token."}, status_code=401)

    email = idinfo.get("email")
    name = idinfo.get("name") or email
    google_sub = idinfo.get("sub")

    if not email:
        return JSONResponse({"success": False, "message": "Google email missing."}, status_code=400)

    # ✅ EXISTING USER
    existing = get_user_by_email(email)
    if existing:
        courier_id = None
        if existing.get("role") == "courier":
            courier = get_courier_by_email(email)
            if courier:
                courier_id = courier.get("courier_id")

        return _build_auth_response(existing, courier_id)

    # ✅ NEW USER (validated role)
    selected_role = requested_role if requested_role in VALID_ROLES else None
    if not selected_role:
        return JSONResponse({"success": False, "message": "Invalid role selection."}, status_code=400)

    result = register_user_with_password(
        name=name,
        email=email,
        password=google_sub,
        selected_role=selected_role,
    )

    if not result["success"]:
        return JSONResponse({"success": False, "message": result["message"]}, status_code=400)

    new_user = result["user"]

    courier_id = None
    if new_user.get("role") == "courier":
        courier = get_courier_by_email(email)
        if courier:
            courier_id = courier.get("courier_id")

    return _build_auth_response(new_user, courier_id)


# ─────────────────────────────────────────────
# Session & Profile Endpoints
# ─────────────────────────────────────────────

@router.post("/api/refresh")
async def api_refresh(intellisupply_refresh_token: str | None = Cookie(default=None)):
    """Silent refresh to issue a new access token and rotate the refresh token cookie."""
    if not intellisupply_refresh_token:
        return JSONResponse(
            {"success": False, "message": "Missing refresh token cookie."},
            status_code=401,
        )

    try:
        user_info = decode_refresh_token(intellisupply_refresh_token)
    except HTTPException as exc:
        return JSONResponse(
            {"success": False, "message": exc.detail},
            status_code=exc.status_code,
        )
    except Exception as exc:
        return JSONResponse(
            {"success": False, "message": f"Invalid refresh token: {str(exc)}"},
            status_code=401,
        )

    user_dict = {
        "id": user_info.id,
        "name": user_info.name,
        "email": user_info.email,
        "role": user_info.role,
        "role_id": user_info.role_id,
    }

    return _build_auth_response(user_dict, courier_id=user_info.courier_id)


@router.post("/api/logout")
async def api_logout():
    """Clear the refresh token cookie to log out the user session."""
    response = JSONResponse({"success": True, "message": "Logged out successfully."})
    response.delete_cookie(
        key="intellisupply_refresh_token",
        path="/",
    )
    return response


@router.get("/api/me")
async def api_get_me(current_user: TokenUser = Depends(get_current_user)):
    """Fetch the authenticated user profile."""
    user_dict = {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "role_id": current_user.role_id,
        "courier_id": current_user.courier_id,
    }
    return {"success": True, "user": user_dict}


@router.patch("/api/me")
async def api_patch_me(
    request: Request,
    current_user: TokenUser = Depends(get_current_user),
):
    """Update user profile name and sync changes with database."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"success": False, "message": "Invalid request body."}, status_code=400)

    name = body.get("name")
    if not name or not isinstance(name, str) or not name.strip():
        return JSONResponse({"success": False, "message": "A valid name is required."}, status_code=400)

    updated_user = update_user_profile(current_user.id, name=name.strip())
    if not updated_user:
        return JSONResponse({"success": False, "message": "Failed to update profile."}, status_code=500)

    courier_id = None
    if updated_user.get("role") == "courier":
        courier = get_courier_by_email(updated_user.get("email"))
        if courier:
            courier_id = courier.get("courier_id")

    serialized = _serialize_user(updated_user, courier_id=courier_id)
    return {"success": True, "user": serialized}
