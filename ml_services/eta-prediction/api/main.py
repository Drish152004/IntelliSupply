"""Legacy standalone ETA API — prefer FastAPI/ gateway."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from fastapi import FastAPI

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config.ml_api import eta_model_path  # noqa: E402
from full_pipeline.inference import ETAPredictor  # noqa: E402

app = FastAPI()

predictor = ETAPredictor.load(eta_model_path())


@app.get("/")
def home():
    return {"status": "running"}


@app.post("/predict")
def predict(order: dict):
    df = pd.DataFrame([order])
    pred = predictor.predict_eta(df)[0]

    return {"eta_minutes": float(pred)}
