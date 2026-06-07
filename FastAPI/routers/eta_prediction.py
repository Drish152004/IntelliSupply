"""ETA prediction API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from dependencies.auth import TokenUser, require_roles
from schemas.eta import ETARequest
from services import eta_prediction as eta_svc

router = APIRouter(prefix="/eta", tags=["eta_prediction"])

LogisticsUser = Annotated[
    TokenUser,
    Depends(require_roles("admin", "logistics_manager")),
]


@router.get("/health")
def health() -> dict[str, str]:
    try:
        from services.registry import init_eta_service

        init_eta_service()
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/predict")
def predict_eta_endpoint(body: ETARequest, current_user: LogisticsUser) -> dict[str, float]:
    del current_user
    try:
        return eta_svc.predict_eta(body.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}") from exc
