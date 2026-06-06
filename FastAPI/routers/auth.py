import os

from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv
from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from bootstrap import BACKEND_ROOT, REPO_ROOT
from aura_graphdb.aura_auth import (
    login_or_register_google_user,
    login_user_with_password,
    register_user_with_password,
)

load_dotenv(REPO_ROOT / ".env")

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


def get_current_user(request: Request):
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
    user = get_current_user(request)
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
