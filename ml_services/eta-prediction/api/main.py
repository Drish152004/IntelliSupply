from fastapi import FastAPI

from api.schemas import ETARequest
from full_pipeline.inference import predict_eta

app = FastAPI()


@app.get("/")
def home():
    return {"message": "ETA Prediction API Running"}


@app.post("/predict")
def predict(request: ETARequest):

    result = predict_eta(request.model_dump())

    return result