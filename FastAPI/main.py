"""
Unified FastAPI gateway for IntelliSupply.

Run from repo root:
  pip install -r FastAPI/requirements.txt
  python FastAPI/run.py

Docs: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import os
import bootstrap  # noqa: F401 — sets up sys.path before other imports
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from security import setup_secure_logging

setup_secure_logging()

from routers import (
    auth,
    copilot,
    dashboard,
    inventory,
    notifications,
    orders,
    eta_prediction,
    users,
    voice,
    planning,
    automation,
)

from services.registry import init_all_services


# ✅ Lifespan (UNCHANGED)
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.service_status = init_all_services()
    yield


app = FastAPI(
    title="IntelliSupply API",
    description="Unified gateway for logistics, ML inference, and auth.",
    version="1.0.0",
    lifespan=lifespan,
)

# ✅ ✅ FINAL CORS CONFIG (AUTH + OAUTH SAFE)
cors_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "")

if cors_origins_str:
    cors_origins = [o.strip() for o in cors_origins_str.split(",") if o.strip()]
else:
    cors_origins = [
        "http://localhost:3000",   # CRA / legacy
        "http://localhost:5173",   # Vite (main)
        "http://127.0.0.1:5173",  # ✅ CRITICAL (cookie + OAuth consistency)
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,  # ✅ REQUIRED for cookies & refresh tokens
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ ✅ AUTH ROUTES (CRITICAL — DO NOT REMOVE)
app.include_router(auth.router)

# ✅ OTHER ROUTERS (UNCHANGED)
app.include_router(copilot.router)
app.include_router(eta_prediction.router)
app.include_router(orders.router)
app.include_router(orders.couriers_router)
app.include_router(users.router)
app.include_router(inventory.router)
app.include_router(dashboard.router)
app.include_router(notifications.router)
app.include_router(voice.router)
app.include_router(planning.router)
app.include_router(automation.router)

# ✅ HEALTH CHECK
@app.get("/health")
def health():
    return {
        "status": "ok",
        "services": getattr(app.state, "service_status", {}),
    }


# ✅ ROOT
@app.get("/")
def root():
    return {
        "message": "IntelliSupply unified API",
        "docs": "/docs",
        "services": {
            "auth": "/login",
            "copilot": "/copilot",
            "voice": "/voice",
            "orders": "/orders",
            "couriers": "/couriers",
            "route": "/route",
            "demand": "/demand",
            "eta": "/eta",
        },
    }