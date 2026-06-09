import pandas as pd
import numpy as np


def load_and_clean(delivery_path, dev_rows=None, seed=42):
    df = pd.read_csv(delivery_path)

    if dev_rows is not None:
        df = df.sample(dev_rows, random_state=seed)

    df["receipt_time"] = pd.to_datetime(df["receipt_time"])
    df["sign_time"] = pd.to_datetime(df["sign_time"])

    df["actual_eta_min"] = (
        (df["sign_time"] - df["receipt_time"]).dt.total_seconds() / 60.0
    )

    df = df[
        (df["actual_eta_min"] > 10)
        & (df["actual_eta_min"] < 300)
    ]

    df = df.dropna(
        subset=["poi_lat", "poi_lng", "receipt_lat", "receipt_lng"]
    )

    return df