"""
Call demand forecasting inference on Hugging Face Space (no local sklearn needed).

Setup (once):
  set HF_TOKEN=hf_...          # Windows
  export HF_TOKEN=hf_...       # Linux/macOS

Usage:
  python -m models.hf_client
"""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_SPACE_URL = os.environ.get(
    "HF_DEMAND_FORECAST_URL",
    "https://deepanrelanto048-intellisupply-demand-forecast.hf.space",
)


def _headers() -> dict[str, str]:
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def health(*, base_url: str | None = None, timeout: float = 30.0) -> dict[str, Any]:
    url = (base_url or DEFAULT_SPACE_URL).rstrip("/")
    with httpx.Client(timeout=timeout) as client:
        r = client.get(f"{url}/health", headers=_headers())
        r.raise_for_status()
        return r.json()


def meta(*, base_url: str | None = None, timeout: float = 30.0) -> dict[str, Any]:
    url = (base_url or DEFAULT_SPACE_URL).rstrip("/")
    with httpx.Client(timeout=timeout) as client:
        r = client.get(f"{url}/meta", headers=_headers())
        r.raise_for_status()
        return r.json()


def predict_demand(
    records: list[dict[str, Any]],
    *,
    base_url: str | None = None,
    timeout: float = 60.0,
) -> list[dict[str, Any]]:
    """
    Run inference on the hosted model.

    Each record needs: city, region_id, day_of_week, month, day_of_month,
    day_of_year, is_weekend, lag_1, lag_2, lag_7, lag_14,
    rolling_mean_7, rolling_std_7, rolling_mean_28.
    """
    url = (base_url or DEFAULT_SPACE_URL).rstrip("/")
    with httpx.Client(timeout=timeout) as client:
        r = client.post(
            f"{url}/predict",
            json={"records": records},
            headers={**_headers(), "Content-Type": "application/json"},
        )
        r.raise_for_status()
        return r.json()["predictions"]


EXAMPLE_RECORD = {
    "city": "Hangzhou",
    "region_id": "56",
    "day_of_week": 2,
    "month": 11,
    "day_of_month": 5,
    "day_of_year": 309,
    "is_weekend": 0,
    "lag_1": 120.0,
    "lag_2": 115.0,
    "lag_7": 98.0,
    "lag_14": 105.0,
    "rolling_mean_7": 110.0,
    "rolling_std_7": 25.0,
    "rolling_mean_28": 108.0,
    "ds": "2024-11-01",
}


if __name__ == "__main__":
    print("Space:", DEFAULT_SPACE_URL)
    print("Health:", health())
    preds = predict_demand([EXAMPLE_RECORD])
    print("Prediction:", preds)
