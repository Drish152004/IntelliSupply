"""Legacy entrypoint — prefer the unified API: fastapi/run.py."""

from fastapi import FastAPI

from eta_inference import ETARequest, predict_eta

app = FastAPI(title="ETA Prediction API (legacy)")


@app.post("/predict")
def predict_eta_endpoint(data: ETARequest):
    return predict_eta(data)


@app.get("/")
def home():
    return {"message": "ETA Prediction API is running. Use fastapi/run.py for the unified gateway."}
