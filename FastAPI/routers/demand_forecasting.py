"""Demand forecasting API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services import demand_forecasting as demand_svc
from services.registry import get_demand_bundle

router = APIRouter(prefix="/demand", tags=["demand_forecasting"])


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
        bundle = get_demand_bundle()
        return {"status": "ok", "granularity": bundle.get("granularity", "daily")}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/meta")
def meta() -> dict[str, Any]:
    try:
        bundle = get_demand_bundle()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    metadata = bundle.get("metadata", {})

    return {
        "feature_cols": bundle.get("feature_cols", []),
        "granularity": bundle.get("granularity", "daily"),
        "holdout_metrics": metadata.get("holdout_metrics", {}),
        "cities": metadata.get("cities", []),
        "last_history_date": metadata.get("last_history_date"),
    }


@router.post("/predict")
def predict_endpoint(body: PredictRequest) -> dict[str, Any]:
    try:
        records = [r.model_dump() for r in body.records]
        return demand_svc.predict_demand(records)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inference failed: {exc}") from exc
