from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
import numpy as np
import pickle

app = FastAPI(title="ETA Prediction API")

# --------------------------
# LOAD MODEL + DATA
# --------------------------
model = pickle.load(open("models/lgbm_eta_model.pkl", "rb"))
features = pickle.load(open("models/features.pkl", "rb"))
cat_mappings = pickle.load(open("models/cat_mappings.pkl", "rb"))

courier_stats = pd.read_pickle("models/courier_stats.pkl")
courier_daily = pd.read_pickle("models/courier_daily.pkl")
courier_hourly = pd.read_pickle("models/courier_hourly.pkl")
aoi_stats = pd.read_pickle("models/aoi_stats.pkl")

# --------------------------
# FIX TYPES (CRITICAL)
# --------------------------
courier_stats["delivery_user_id"] = courier_stats["delivery_user_id"].astype(str)
courier_daily["delivery_user_id"] = courier_daily["delivery_user_id"].astype(str)
courier_hourly["delivery_user_id"] = courier_hourly["delivery_user_id"].astype(str)

aoi_stats["aoi_id"] = aoi_stats["aoi_id"].astype(str)

# --------------------------
# INPUT SCHEMA
# --------------------------
class ETARequest(BaseModel):
    delivery_user_id: int
    from_dipan_id: int
    aoi_id: int

    receipt_time: str

    receipt_lat: float
    receipt_lng: float

    poi_lat: float
    poi_lng: float


# --------------------------
# FEATURE ENGINEERING
# --------------------------
def build_features(data: ETARequest):

    df = pd.DataFrame([data.dict()])

    # ✅ MATCH TRAINING TYPES
    df["delivery_user_id"] = df["delivery_user_id"].astype(str)
    df["from_dipan_id"] = df["from_dipan_id"].astype(str)
    df["aoi_id"] = df["aoi_id"].astype(str)

    # --------------------------
    # TIME FEATURES
    # --------------------------
    df["receipt_time"] = pd.to_datetime(df["receipt_time"])
    df["hour"] = df["receipt_time"].dt.hour
    df["weekday"] = df["receipt_time"].dt.weekday
    df["ds"] = df["receipt_time"].dt.dayofyear

    # --------------------------
    # DISTANCE
    # --------------------------
    # df["distance_km"] = np.sqrt(
    #     (df["receipt_lat"] - df["poi_lat"]) ** 2 +
    #     (df["receipt_lng"] - df["poi_lng"]) ** 2
    # ) / 1000

    df["distance_km"] = np.sqrt(
    (df["receipt_lat"] - df["poi_lat"])**2 +
    (df["receipt_lng"] - df["poi_lng"])**2
    ) * 111

    df["distance_hour_interaction"] = df["distance_km"] * df["hour"]

    # --------------------------
    # COURIER FEATURES
    # --------------------------
    df = df.merge(
        courier_stats[[
            "delivery_user_id",
            "courier_avg_eta",
            "courier_order_count"
        ]],
        on="delivery_user_id",
        how="left"
    )

    df = df.merge(
        courier_daily,
        on=["delivery_user_id", "ds"],
        how="left"
    )

    df = df.merge(
        courier_hourly,
        on=["delivery_user_id", "ds", "hour"],
        how="left"
    )

    # --------------------------
    # AOI FEATURES
    # --------------------------
    df = df.merge(
        aoi_stats[[
            "aoi_id",
            "aoi_mean_eta",
            "aoi_count"
        ]],
        on="aoi_id",
        how="left"
    )

    # --------------------------
    # HANDLE MISSING
    # --------------------------
    mean_eta = courier_stats["courier_avg_eta"].mean()

    df["courier_hourly_load"] = df["courier_hourly_load"].fillna(0)
    df["courier_daily_load"] = df["courier_daily_load"].fillna(0)
    df["courier_avg_eta"] = df["courier_avg_eta"].fillna(mean_eta)
    df["courier_order_count"] = df["courier_order_count"].fillna(0)

    df = df.fillna(0)

    # --------------------------
    # ENCODE CATEGORICAL USING TRAINING MAPPINGS
    # --------------------------
    for col in ["aoi_id", "delivery_user_id", "from_dipan_id"]:
        if col in df.columns:
            categories = cat_mappings.get(col, []) + ["missing"]
            df[col] = pd.Categorical(df[col], categories=categories)
            df[col] = df[col].fillna("missing")

    # --------------------------
    # ALIGN FEATURES
    # --------------------------
    for col in features:
        if col not in df.columns:
            df[col] = 0

    df = df[features]

    return df


# --------------------------
# PREDICT
# --------------------------
@app.post("/predict")
def predict_eta(data: ETARequest):

    X = build_features(data)
    pred = model.predict(X)[0]

    return {
        "eta_minutes": round(float(pred), 2)
    }


# --------------------------
# HEALTH CHECK
# --------------------------
@app.get("/")
def home():
    return {
        "message": "ETA Prediction API is running ✅"
    }