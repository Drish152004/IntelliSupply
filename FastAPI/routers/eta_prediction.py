"""ETA prediction API routes."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

ETA_SRC = Path(__file__).resolve().parents[2] / "ml_services" / "eta-prediction" / "src"
if str(ETA_SRC) not in sys.path:
    sys.path.insert(0, str(ETA_SRC))

from eta_inference import ETARequest  # noqa: E402

from services import eta_prediction as eta_svc  # noqa: E402

router = APIRouter(prefix="/eta", tags=["eta_prediction"])


@router.get("/health")
def health() -> dict[str, str]:
    try:
        from services.registry import init_eta_service

        init_eta_service()
        return {"status": "ok"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/predict")
def predict_eta_endpoint(body: ETARequest) -> dict[str, float]:
    try:
        return eta_svc.predict_eta(body.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}") from exc
