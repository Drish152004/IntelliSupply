"""
Unified FastAPI gateway for IntelliSupply ML services.

Run from repo root:
  pip install -r fastapi/requirements.txt
  python fastapi/run.py

Docs: http://127.0.0.1:8000/docs
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

FASTAPI_ROOT = Path(__file__).resolve().parent
if str(FASTAPI_ROOT) not in sys.path:
    sys.path.insert(0, str(FASTAPI_ROOT))

from routers import demand_forecasting, eta_prediction, route_prediction  # noqa: E402
from services.registry import init_all_services  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.service_status = init_all_services()
    yield


app = FastAPI(
    title="IntelliSupply ML API",
    description="Centralized inference for route prediction, demand forecasting, and ETA.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(route_prediction.router)
app.include_router(demand_forecasting.router)
app.include_router(eta_prediction.router)


@app.get("/health")
def health():
    return {"status": "ok", "services": app.state.service_status}


@app.get("/")
def root():
    return {
        "message": "IntelliSupply unified ML API",
        "docs": "/docs",
        "services": {
            "route": "/route",
            "demand": "/demand",
            "eta": "/eta",
        },
    }
