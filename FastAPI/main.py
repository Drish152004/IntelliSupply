"""
Unified FastAPI gateway for IntelliSupply.

Run from repo root:
  pip install -r FastAPI/requirements.txt
  python FastAPI/run.py

Docs: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import bootstrap  # noqa: F401 — sets up sys.path before other imports
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bootstrap import REPO_ROOT
from routers import auth, demand_forecasting, orders, route_prediction, eta_prediction
from routers.auth import configure_auth
from services.registry import init_all_services


def _load_copilot_router():
    """Load copilot routes under a dedicated module name (avoids `api` package clash)."""
    import importlib.util
    import sys

    if "intellisupply_copilot" in sys.modules:
        return sys.modules["intellisupply_copilot"].router

    pkg_path = REPO_ROOT / "api"
    spec = importlib.util.spec_from_file_location(
        "intellisupply_copilot",
        pkg_path / "__init__.py",
        submodule_search_locations=[str(pkg_path)],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load copilot API from {pkg_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules["intellisupply_copilot"] = module
    spec.loader.exec_module(module)
    return module.router


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

configure_auth(app)

copilot_router = _load_copilot_router()
app.include_router(copilot_router)
app.include_router(route_prediction.router)
app.include_router(demand_forecasting.router)
app.include_router(eta_prediction.router)
app.include_router(orders.router)
app.include_router(orders.couriers_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "services": getattr(app.state, "service_status", {}),
    }


@app.get("/")
def root():
    return {
        "message": "IntelliSupply unified API",
        "docs": "/docs",
        "services": {
            "auth": "/login",
            "copilot": "/copilot",
            "orders": "/orders",
            "couriers": "/couriers",
            "route": "/route",
            "demand": "/demand",
            "eta": "/eta",
        },
    }
