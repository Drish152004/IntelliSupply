"""Tests for ETA production wrapper."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.wrappers.eta_wrapper import ETAWrapper

CONTEXT_PAYLOAD = {
    "delivery_user_id": "C001",
    "from_dipan_id": "42",
    "aoi_id": "7",
    "receipt_lat": 30.6,
    "receipt_lng": 104.0,
    "poi_lat": 30.61,
    "poi_lng": 104.01,
    "receipt_time": "2026-06-05T12:00:00",
}


def _fake_inference_module() -> types.ModuleType:
    module = types.ModuleType("full_pipeline.inference")
    module.predict_eta = MagicMock(return_value={"eta_minutes": 42.5})
    return module


@patch("ml.wrappers.eta_wrapper._ensure_eta_path")
def test_eta_wrapper_normalizes_prediction(mock_ensure_path) -> None:
    fake_inference = _fake_inference_module()
    fake_package = types.ModuleType("full_pipeline")

    with patch.dict(
        sys.modules,
        {
            "full_pipeline": fake_package,
            "full_pipeline.inference": fake_inference,
        },
    ):
        result = ETAWrapper().run(CONTEXT_PAYLOAD)

    assert result["prediction_type"] == "eta"
    assert result["model_name"] == "lgbm_eta_model"
    assert result["result"] == {"eta_minutes": 42.5}
    fake_inference.predict_eta.assert_called_once()
    mock_ensure_path.assert_called_once()


@patch("ml.wrappers.eta_wrapper._ensure_eta_path")
def test_eta_wrapper_propagates_model_errors(mock_ensure_path) -> None:
    fake_inference = types.ModuleType("full_pipeline.inference")
    fake_inference.predict_eta = MagicMock(side_effect=RuntimeError("model unavailable"))
    fake_package = types.ModuleType("full_pipeline")

    with patch.dict(
        sys.modules,
        {
            "full_pipeline": fake_package,
            "full_pipeline.inference": fake_inference,
        },
    ):
        with pytest.raises(RuntimeError, match="model unavailable"):
            ETAWrapper().run(CONTEXT_PAYLOAD)
