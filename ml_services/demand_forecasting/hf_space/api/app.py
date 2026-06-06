"""Demand forecasting inference API for Hugging Face Space (port 7860)."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

PKG = Path(__file__).resolve().parents[1]
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))

from inference import DEFAULT_FEATURE_COLS, load_bundle, predict  # noqa: E402

app = FastAPI(
    title="IntelliSupply Demand Forecasting",
    version="1.0.0",
    description="Regional package demand inference from trained .pkl model.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/")
def root():
    return {
        "service": "IntelliSupply Demand Forecasting",
        "docs": "/docs",
        "predict": "POST /predict",
        "meta": "GET /meta",
    }


@app.get("/health")
def health():
    pkl = PKG / "models" / "lade_demand_forecaster.pkl"
    return {"ok": pkl.exists(), "model_path": str(pkl)}


@app.get("/meta")
def meta():
    try:
        bundle = load_bundle()
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    metadata = bundle.get("metadata", {})
    return {
        "feature_cols": bundle.get("feature_cols", DEFAULT_FEATURE_COLS),
        "granularity": bundle.get("granularity", "daily"),
        "holdout_metrics": metadata.get("holdout_metrics", {}),
        "cities": metadata.get("cities", []),
        "last_history_date": metadata.get("last_history_date"),
    }


@app.post("/predict")
def predict_endpoint(body: PredictRequest):
    try:
        records = [r.model_dump() for r in body.records]
        return {"predictions": predict(records)}
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Inference failed: {exc}") from exc
