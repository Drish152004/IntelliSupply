"""Demand forecasting API routes."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from dependencies.auth import TokenUser, get_current_user, require_roles
from services import demand_forecasting as demand_svc

router = APIRouter(prefix="/demand", tags=["demand_forecasting"])

AuthenticatedUser = Annotated[TokenUser, Depends(get_current_user)]
LogisticsUser = Annotated[
    TokenUser,
    Depends(require_roles("admin", "logistics_manager", "inventory_manager")),
]


class FeatureRecord(BaseModel):
    city: str = Field(..., examples=["Hangzhou"])
    region_id: str = Field(..., examples=["56"])
    day_of_week: int = Field(..., ge=0, le=6, examples=[2])
    month: int = Field(..., ge=1, le=12, examples=[11])
    day_of_month: int = Field(..., ge=1, le=31, examples=[5])
    day_of_year: int = Field(..., ge=1, le=366, examples=[309])
    is_weekend: int = Field(..., ge=0, le=1, examples=[0])
    lag_1: float = Field(..., ge=0, examples=[120.0])
    lag_2: float = Field(..., ge=0, examples=[115.0])
    lag_7: float = Field(..., ge=0, examples=[98.0])
    lag_14: float = Field(..., ge=0, examples=[105.0])
    rolling_mean_7: float = Field(..., ge=0, examples=[110.0])
    rolling_std_7: float = Field(..., ge=0, examples=[25.0])
    rolling_mean_28: float = Field(..., ge=0, examples=[108.0])
    ds: str | None = Field(None, examples=["2024-11-01"])


class PredictRequest(BaseModel):
    records: list[FeatureRecord] = Field(..., min_length=1)


@router.get("/health")
def health() -> dict[str, Any]:
    try:
        return demand_svc.check_health()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/meta")
def meta(current_user: AuthenticatedUser) -> dict[str, Any]:
    del current_user
    try:
        return demand_svc.get_meta()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/predict")
def predict_endpoint(body: PredictRequest, current_user: LogisticsUser) -> dict[str, Any]:
    del current_user
    try:
        records = [r.model_dump() for r in body.records]
        return demand_svc.predict_demand(records)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Inference failed: {exc}") from exc
