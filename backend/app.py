import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth


# ---------------------------------------------------------
# Make project root importable
# This allows: from aura_graphdb.aura_auth import ...
# ---------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from aura_graphdb.aura_auth import (
    register_user_with_password,
    login_user_with_password,
    login_or_register_google_user
)


load_dotenv(BASE_DIR / ".env")


app = FastAPI(title="IntelliSupply Auth Backend")


# ---------------------------------------------------------
# Session middleware
# ---------------------------------------------------------
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("FASTAPI_SECRET_KEY", "dev-secret-change-this")
)


# ---------------------------------------------------------
# Templates and static
# ---------------------------------------------------------
templates = Jinja2Templates(directory=str(BASE_DIR / "backend" / "templates"))

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "backend" / "static")),
    name="static"
)


# ---------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------
oauth = OAuth()

oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile"
    }
)


ROLES = [
    ("courier", "Courier"),
    ("inventory_manager", "Inventory Manager"),
    ("logistics_manager", "Logistics Manager")
]


# ---------------------------------------------------------
# Helper
# ---------------------------------------------------------
def redirect_to(path: str):
    return RedirectResponse(url=path, status_code=303)


def get_current_user(request: Request):
    return request.session.get("user")


# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------
@app.get("/")
async def home(request: Request):
    user = get_current_user(request)

    if user:
        return redirect_to("/dashboard")

    return redirect_to("/login")


@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse(
        request,
        "register.html",
        {
            "roles": ROLES,
            "message": request.session.pop("message", None)
        }
    )
@app.post("/register")
async def register_user(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form("courier")
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
        selected_role=role
    )

    if not result["success"]:
        request.session["message"] = result["message"]
        return redirect_to("/register")

    request.session["user"] = result["user"]
    return redirect_to("/dashboard")


@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "message": request.session.pop("message", None)
        }
    )

@app.post("/login")
async def login_user(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    result = login_user_with_password(
        email=email.strip(),
        password=password.strip()
    )

    if not result["success"]:
        request.session["message"] = result["message"]
        return redirect_to("/login")

    request.session["user"] = result["user"]
    return redirect_to("/dashboard")


@app.get("/auth/google")
async def google_login(request: Request, role: str = "courier"):
    request.session["pending_google_role"] = role

    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")

    if not redirect_uri:
        redirect_uri = str(request.url_for("google_callback"))

    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/google/callback")
async def google_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        request.session["message"] = f"Google login failed: {str(e)}"
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
        selected_role=selected_role
    )

    if not result["success"]:
        request.session["message"] = result["message"]
        return redirect_to("/login")

    request.session["user"] = result["user"]
    return redirect_to("/dashboard")

@app.get("/dashboard")
async def dashboard(request: Request):
    user = get_current_user(request)

    if not user:
        return redirect_to("/login")

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "user": user
        }
    )

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return redirect_to("/login")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "IntelliSupply FastAPI Auth Backend"
    }