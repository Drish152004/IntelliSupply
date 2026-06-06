"""Route prediction API routes."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

ROUTE_ROOT = Path(__file__).resolve().parents[2] / "ml_services" / "route_prediction"
if str(ROUTE_ROOT) not in sys.path:
    sys.path.insert(0, str(ROUTE_ROOT))

from api.schemas import (  # noqa: E402
    HealthResponse,
    NextStopRequest,
    NextStopResponse,
    RouteSequenceRequest,
    RouteSequenceResponse,
)
from services import route_prediction as route_svc  # noqa: E402
from services.registry import get_route_predictor, route_model_path  # noqa: E402

router = APIRouter(prefix="/route", tags=["route_prediction"])


@router.get("/health", response_model=HealthResponse)
def health():
    try:
        pred = get_route_predictor()
        path = route_model_path()
        return HealthResponse(
            status="ok",
            model_version=pred.version,
            model_path=str(path.resolve()),
            feature_count=len(pred.feature_cols),
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/predict/next-stop", response_model=NextStopResponse)
def predict_next_stop(body: NextStopRequest):
    try:
        result = route_svc.predict_next_stop(body.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return NextStopResponse(**result)


@router.post("/predict/route", response_model=RouteSequenceResponse)
def predict_route(body: RouteSequenceRequest):
    try:
        result = route_svc.predict_route_sequence(body.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RouteSequenceResponse(**result)
