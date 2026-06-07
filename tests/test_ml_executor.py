"""Tests for MLExecutor routing and error handling."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.ml_executor import MLExecutor
from ml.model_router import ModelRouter, UnsupportedMLTaskError
from ml.validators import PayloadValidationError

ETA_PAYLOAD = {
    "delivery_user_id": "C001",
    "from_dipan_id": "42",
    "aoi_id": "7",
    "receipt_lat": 30.6,
    "receipt_lng": 104.0,
    "poi_lat": 30.61,
    "poi_lng": 104.01,
    "receipt_time": "2026-06-05T12:00:00",
}


def test_model_router_maps_tasks() -> None:
    assert ModelRouter.get_wrapper("eta_prediction").prediction_type == "eta"
    assert ModelRouter.get_wrapper("route_prediction").prediction_type == "route"
    assert ModelRouter.get_wrapper("demand_forecast").prediction_type == "demand_forecast"


def test_model_router_rejects_unknown_task() -> None:
    with pytest.raises(UnsupportedMLTaskError):
        ModelRouter.get_wrapper("unknown_task")


@patch.object(ModelRouter, "get_wrapper")
def test_ml_executor_returns_normalized_success(mock_get_wrapper) -> None:
    mock_wrapper = MagicMock()
    mock_wrapper.run.return_value = {
        "prediction_type": "eta",
        "model_name": "lgbm_eta_model",
        "result": {"eta_minutes": 33.0},
    }
    mock_get_wrapper.return_value = mock_wrapper

    outcome = MLExecutor().execute("eta_prediction", ETA_PAYLOAD)

    assert outcome.success is True
    assert outcome.prediction_type == "eta"
    assert outcome.model_name == "lgbm_eta_model"
    assert outcome.result == {"eta_minutes": 33.0}
    assert outcome.duration_ms >= 0
    assert outcome.error_message is None

    state_fields = outcome.to_state_fields()
    assert state_fields["execution_status"] == "success"
    assert state_fields["prediction_result"]["eta_minutes"] == 33.0

    response = outcome.to_agent_response(task="eta_prediction")
    assert '"status": "prediction_complete"' in response
    assert '"eta_minutes": 33.0' in response


@patch.object(ModelRouter, "get_wrapper")
def test_ml_executor_returns_structured_model_error(mock_get_wrapper) -> None:
    mock_wrapper = MagicMock()
    mock_wrapper.run.side_effect = RuntimeError("CUDA OOM")
    mock_get_wrapper.return_value = mock_wrapper

    outcome = MLExecutor().execute("eta_prediction", ETA_PAYLOAD)

    assert outcome.success is False
    assert outcome.prediction_type is None
    assert outcome.error_message is not None
    assert "ETA model execution failed" in outcome.error_message

    response = outcome.to_agent_response(task="eta_prediction")
    assert '"status": "error"' in response
    assert '"stage": "ml_execution"' in response


@patch.object(ModelRouter, "get_wrapper")
def test_ml_executor_handles_validation_errors(mock_get_wrapper) -> None:
    mock_wrapper = MagicMock()
    mock_wrapper.run.side_effect = PayloadValidationError("Missing required ETA fields: receipt_time")
    mock_get_wrapper.return_value = mock_wrapper

    outcome = MLExecutor().execute("eta_prediction", ETA_PAYLOAD)

    assert outcome.success is False
    assert "payload validation failed" in (outcome.error_message or "")


def test_ml_executor_handles_unsupported_task() -> None:
    outcome = MLExecutor().execute("eta_lookup", ETA_PAYLOAD)

    assert outcome.success is False
    assert outcome.error_message is not None
    assert "No ML wrapper registered" in outcome.error_message
