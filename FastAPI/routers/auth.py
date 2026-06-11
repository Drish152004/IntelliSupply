"""
JWT + OAuth authentication API for IntelliSupply (SPA-friendly).

- Stateless JWT (access + refresh)
- API-based Google OAuth (no sessions)
- Compatible with React + Agentic AI
"""

from __future__ import annotations

import os
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from dependencies.auth import (
    TokenUser,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_current_user,
    get_current_user_optional,
)

from aura_graphdb.aura_auth import (
    count_profiles,
    get_user_by_email,
    get_user_by_id,
    login_user_with_password,
    register_user_with_password,
    update_user_profile,
)

from aura_graphdb.aura_courier import get_courier_by_email

# Google OAuth
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests


router = APIRouter(tags=["auth"])


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

    response.set_cookie(
        key="intellisupply_refresh_token",
        value=refresh_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
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

@router.post("/api/login")
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


@router.post("/api/register")
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

    result = register_user_with_password(
        name=name,
        email=email,
        password=password,
        selected_role=role,
    )

    if not result["success"]:
        return JSONResponse({"success": False, "message": result["message"]}, status_code=422)

    return _build_auth_response(result["user"]), 201


# ─────────────────────────────────────────────
# Google OAuth (FIXED ✅)
# ─────────────────────────────────────────────

@router.post("/api/google-login")
async def google_login(request: Request):
    try:
        body = await request.json()
        token = body.get("id_token")
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

    # ✅ CHECK USER IN POSTGRES
    user = get_user_by_email(email)

    if user:
        courier_id = None
        if user.get("role") == "courier":
            courier = get_courier_by_email(email)
            if courier:
                courier_id = courier.get("courier_id")

        return _build_auth_response(user, courier_id)

    # ✅ REGISTER NEW USER (uses existing system)
    result = register_user_with_password(
        name=name,
        email=email,
        password=google_sub,
        selected_role="courier",
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
# Token Refresh / Logout
# ─────────────────────────────────────────────

@router.post("/api/refresh")
async def api_refresh(request: Request):
    refresh_token = request.cookies.get("intellisupply_refresh_token")

    if not refresh_token:
        return JSONResponse({"success": False, "message": "Missing refresh token."}, status_code=401)

    try:
        user = decode_refresh_token(refresh_token)
    except Exception:
        return JSONResponse({"success": False, "message": "Invalid refresh token."}, status_code=401)

    serialized = {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "role_id": user.role_id,
        "role": user.role,
    }
    if user.courier_id:
        serialized["courier_id"] = user.courier_id

    access_token = create_access_token({**serialized})

    return JSONResponse({
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "user": serialized,
    })


@router.post("/api/logout")
async def api_logout():
    response = JSONResponse({"success": True})
    response.delete_cookie("intellisupply_refresh_token", path="/")
    return response


# ─────────────────────────────────────────────
# User Profile
# ─────────────────────────────────────────────

@router.get("/api/me")
async def api_me(current_user: TokenUser = Depends(get_current_user)):
    if current_user.role == "courier":
        courier = get_courier_by_email(current_user.email)
        if courier:
            return JSONResponse({
                "success": True,
                "user": _serialize_user(
                    {
                        "id": courier["courier_id"],
                        "name": courier["name"],
                        "email": courier["email"],
                        "role_id": courier.get("role_id"),
                        "role": "courier",
                    },
                    courier_id=courier["courier_id"],
                ),
            })

    profile = get_user_by_id(current_user.id)

    if not profile:
        return JSONResponse({"success": False, "message": "User not found."}, status_code=404)

    return JSONResponse({
        "success": True,
        "user": _serialize_user(profile),
    })


@router.patch("/api/me")
async def api_update_me(
    body: ProfileUpdateRequest,
    current_user: TokenUser = Depends(get_current_user),
):
    if current_user.role == "courier":
        return JSONResponse({"success": False, "message": "Not supported."}, status_code=422)

    updated = update_user_profile(current_user.id, name=body.name)

    if not updated:
        return JSONResponse({"success": False, "message": "User not found."}, status_code=404)

    return JSONResponse({
        "success": True,
        "user": _serialize_user(updated),
    })
