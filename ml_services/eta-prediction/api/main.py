from fastapi import FastAPI
import pandas as pd
from pathlib import Path

from full_pipeline.inference import ETAPredictor

app = FastAPI()

MODEL_PATH = Path(__file__).resolve().parent.parent / "models/eta_lightgbm_model.pkl"

predictor = ETAPredictor.load(MODEL_PATH)


@app.get("/")
def home():
    return {"status": "running"}


@app.post("/predict")
def predict(order: dict):
    df = pd.DataFrame([order])
    pred = predictor.predict_eta(df)[0]

    return {"eta_minutes": float(pred)}
