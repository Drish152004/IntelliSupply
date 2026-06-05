"""Pre-processing module for raw delivery data."""

import pandas as pd
import numpy as np

def preprocess_data(csv_path: str) -> pd.DataFrame:
    """Load and clean the raw delivery data, calculating base fields."""
    print(f"Loading raw data from {csv_path}...")
    delivery = pd.read_csv(csv_path)
    
    # clean index columns
    delivery = delivery.drop(columns=["Unnamed: 0"], errors="ignore")
    
    # time parsing and eta_minutes calculation
    delivery["receipt_time"] = pd.to_datetime(delivery["receipt_time"])
    delivery["sign_time"] = pd.to_datetime(delivery["sign_time"])
    
    delivery["eta_minutes"] = (
        (delivery["sign_time"] - delivery["receipt_time"])
        .dt.total_seconds() / 60
    )
    
    # clean ETA range
    delivery = delivery[(delivery["eta_minutes"] > 1) & (delivery["eta_minutes"] < 300)]
    
    # time features
    delivery["hour"] = delivery["receipt_time"].dt.hour
    delivery["weekday"] = delivery["receipt_time"].dt.weekday

    
    # spatial features
    delivery["distance_km"] = np.sqrt(
        (delivery["receipt_lat"] - delivery["poi_lat"])**2 +
        (delivery["receipt_lng"] - delivery["poi_lng"])**2
    ) / 1000
    
    # interaction
    delivery["distance_hour_interaction"] = delivery["distance_km"] * delivery["hour"]
    
    return delivery
