"""ETA prediction inference helpers."""

from __future__ import annotations

from typing import Any
import pandas as pd

from services.registry import _ensure_eta_path, get_eta_predictor


def predict_eta(payload: dict[str, Any]) -> dict[str, float]:
    _ensure_eta_path()
    predictor = get_eta_predictor()
    
    # Ensure robustness by injecting defaults for missing or None fields
    full_payload = {
        "city_name": "",
        "typecode": "",
        **payload
    }
    if full_payload.get("city_name") is None:
        full_payload["city_name"] = ""
    if full_payload.get("typecode") is None:
        full_payload["typecode"] = ""

    frame = pd.DataFrame([full_payload])
    minutes = float(predictor.predict_eta(frame)[0])
    return {"eta_minutes": minutes}
