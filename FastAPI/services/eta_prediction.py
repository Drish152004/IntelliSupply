"""ETA prediction inference helpers."""

from __future__ import annotations

from typing import Any

from services.registry import _ensure_eta_path, ensure_eta_service


def predict_eta(payload: dict[str, Any]) -> dict[str, float]:
    _ensure_eta_path()
    from eta_inference import ETARequest, predict_eta as _predict

    ensure_eta_service()
    return _predict(ETARequest(**payload))
