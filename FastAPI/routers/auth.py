"""JWT authentication API for the React frontend."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from aura_graphdb.aura_auth import (
    count_profiles,
    get_user_by_email,
    get_user_by_id,
    login_user_with_password,
    register_user_with_password,
    update_user_profile,
)
from aura_graphdb.aura_courier import get_courier_by_email
from dependencies.auth import (
    TokenUser,
    create_access_token,
    get_current_user,
    get_current_user_optional,
)

router = APIRouter(tags=["auth"])


class ProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)


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


def _auth_response(user: dict, *, courier_id: str | None = None) -> dict:
    serialized = _serialize_user(user, courier_id=courier_id)
    token = create_access_token({**serialized, "courier_id": courier_id})
    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer",
        "user": serialized,
    }


def _try_login(email: str, password: str) -> dict | None:
    profile = get_user_by_email(email)
    if not profile:
        return None

    result = login_user_with_password(email=email, password=password)
    if not result["success"]:
        return None

    user = result["user"]
    courier_id = None
    if user.get("role") == "courier":
        courier = get_courier_by_email(email)
        if courier:
            courier_id = courier.get("courier_id")

    return _auth_response(user, courier_id=courier_id)


@router.post("/api/login")
async def api_login(request: Request):
    """JSON login endpoint for the React frontend. Returns JWT access token."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"success": False, "message": "Invalid request body."}, status_code=400)

    email = (body.get("email") or "").strip()
    password = (body.get("password") or "").strip()

    if not email or not password:
        return JSONResponse({"success": False, "message": "Email and password are required."}, status_code=400)

    try:
        auth_payload = _try_login(email, password)
    except Exception as exc:
        return JSONResponse({"success": False, "message": str(exc)}, status_code=503)

    if not auth_payload:
        return JSONResponse({"success": False, "message": "Invalid email or password."}, status_code=401)

    return JSONResponse(auth_payload)


@router.post("/api/register")
async def api_register(
    request: Request,
    current_user: TokenUser | None = Depends(get_current_user_optional),
):
    """JSON register endpoint for the React frontend. Returns JWT access token."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"success": False, "message": "Invalid request body."}, status_code=400)

    name = (body.get("name") or "").strip()
    email = (body.get("email") or "").strip()
    password = (body.get("password") or "").strip()
    role = (body.get("role") or "courier").strip()

    if not name or not email or not password:
        return JSONResponse({"success": False, "message": "Name, email, and password are required."}, status_code=400)

    if count_profiles() > 0:
        if current_user is None or current_user.role != "admin":
            return JSONResponse(
                {"success": False, "message": "Admin authentication required to register users."},
                status_code=403,
            )

    try:
        result = register_user_with_password(name=name, email=email, password=password, selected_role=role)
    except Exception as exc:
        return JSONResponse({"success": False, "message": str(exc)}, status_code=503)

    if not result["success"]:
        return JSONResponse({"success": False, "message": result["message"]}, status_code=422)

    return JSONResponse(_auth_response(result["user"]), status_code=201)


@router.get("/api/me")
async def api_me(current_user: TokenUser = Depends(get_current_user)):
    if current_user.role == "courier":
        courier = get_courier_by_email(current_user.email)
        if courier:
            return JSONResponse(
                {
                    "success": True,
                    "user": _serialize_user(
                        {
                            "id": courier["courier_id"],
                            "name": courier["name"],
                            "email": courier["email"],
                            "role_id": courier.get("role_id"),
                            "role": courier.get("role") or "courier",
                        },
                        courier_id=courier["courier_id"],
                    ),
                }
            )

    profile = get_user_by_id(current_user.id)
    if not profile:
        return JSONResponse({"success": False, "message": "User not found."}, status_code=404)

    return JSONResponse({"success": True, "user": _serialize_user(profile)})


@router.patch("/api/me")
async def api_update_me(
    body: ProfileUpdateRequest,
    current_user: TokenUser = Depends(get_current_user),
):
    if current_user.role == "courier":
        return JSONResponse(
            {"success": False, "message": "Courier profile updates are not supported yet."},
            status_code=422,
        )

    updated = update_user_profile(current_user.id, name=body.name)
    if not updated:
        return JSONResponse({"success": False, "message": "User not found."}, status_code=404)

    return JSONResponse({"success": True, "user": _serialize_user(updated)})
