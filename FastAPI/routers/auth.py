import os

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from bootstrap import BACKEND_ROOT
from dependencies.auth import create_access_token, get_current_user, get_current_user_optional, TokenUser
from aura_graphdb.aura_auth import (
    count_profiles,
    get_user_by_id,
    login_or_register_google_user,
    login_user_with_password,
    register_user_with_password,
    update_user_profile,
)
from aura_graphdb.aura_courier import get_courier_by_email, login_courier

router = APIRouter(tags=["auth"])

templates = Jinja2Templates(directory=str(BACKEND_ROOT / "templates"))

oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

ROLES = [
    ("courier", "Courier"),
    ("inventory_manager", "Inventory Manager"),
    ("logistics_manager", "Logistics Manager"),
]


def redirect_to(path: str):
    return RedirectResponse(url=path, status_code=303)


def get_session_user(request: Request):
    return request.session.get("user")


def configure_auth(app) -> None:
    """Session middleware, static files, and auth routes."""
    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("FASTAPI_SECRET_KEY", "dev-secret-change-this"),
    )
    app.mount(
        "/static",
        StaticFiles(directory=str(BACKEND_ROOT / "static")),
        name="static",
    )
    app.include_router(router)


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {"message": request.session.pop("message", None)},
    )


@router.post("/login")
async def login_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    result = login_user_with_password(
        email=email.strip(),
        password=password.strip(),
    )

    if not result["success"]:
        request.session["message"] = result["message"]
        return redirect_to("/login")

    request.session["user"] = result["user"]
    return redirect_to("/dashboard")


@router.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse(
        request,
        "register.html",
        {
            "roles": ROLES,
            "message": request.session.pop("message", None),
        },
    )


@router.post("/register")
async def register_user(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("courier"),
):
    name = name.strip()
    email = email.strip()
    password = password.strip()

    if not name or not email or not password:
        request.session["message"] = "Name, email, and password are required."
        return redirect_to("/register")

    result = register_user_with_password(
        name=name,
        email=email,
        password=password,
        selected_role=role,
    )

    if not result["success"]:
        request.session["message"] = result["message"]
        return redirect_to("/register")

    request.session["user"] = result["user"]
    return redirect_to("/dashboard")


@router.get("/auth/google")
async def google_login(request: Request, role: str = "courier"):
    request.session["pending_google_role"] = role

    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    if not redirect_uri:
        redirect_uri = str(request.url_for("google_callback"))

    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/google/callback", name="google_callback")
async def google_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as exc:
        request.session["message"] = f"Google login failed: {str(exc)}"
        return redirect_to("/login")

    userinfo = token.get("userinfo")
    if not userinfo:
        userinfo = await oauth.google.userinfo(token=token)

    email = userinfo.get("email")
    name = userinfo.get("name") or email
    google_sub = userinfo.get("sub")

    if not email or not google_sub:
        request.session["message"] = "Google login failed. Missing email or user ID."
        return redirect_to("/login")

    selected_role = request.session.pop("pending_google_role", "courier")

    result = login_or_register_google_user(
        name=name,
        email=email,
        google_sub=google_sub,
        selected_role=selected_role,
    )

    if not result["success"]:
        request.session["message"] = result["message"]
        return redirect_to("/login")

    request.session["user"] = result["user"]
    return redirect_to("/dashboard")


@router.get("/dashboard")
async def dashboard(request: Request):
    user = get_session_user(request)
    if not user:
        return redirect_to("/login")

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"user": user},
    )


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return redirect_to("/login")


# ─── JSON API endpoints for the React frontend ────────────────────────────────

from fastapi import Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


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
    from aura_graphdb.supabase_auth import get_user_by_email

    profile = get_user_by_email(email)
    if profile:
        result = login_user_with_password(email=email, password=password)
        if result["success"]:
            return _auth_response(result["user"])
        return None

    courier_result = login_courier(email=email, password=password)
    if courier_result["success"]:
        courier = courier_result["courier"]
        user = {
            "id": courier["courier_id"],
            "name": courier["name"],
            "email": courier["email"],
            "role_id": courier.get("role_id"),
            "role": courier.get("role") or "courier",
        }
        return _auth_response(user, courier_id=courier["courier_id"])

    return None


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
