"""Tests for demand forecast HF wrapper."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.wrappers.demand_wrapper import DemandWrapper

HF_RECORD = {
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
}

CONTEXT_PAYLOAD = {"records": [HF_RECORD]}


def test_demand_wrapper_calls_hf_client() -> None:
    mock_client = MagicMock()
    mock_client.predict_demand.return_value = [
        {"city": "Hangzhou", "region_id": "56", "predicted_demand": 42.0}
    ]

    result = DemandWrapper(client=mock_client).run(CONTEXT_PAYLOAD)

    assert result["prediction_type"] == "demand_forecast"
    assert result["model_name"] == "lade_demand_forecaster"
    assert result["result"]["predictions"][0]["predicted_demand"] == 42.0
    mock_client.predict_demand.assert_called_once_with([HF_RECORD])


def test_demand_wrapper_requires_records() -> None:
    with pytest.raises(Exception, match="records"):
        DemandWrapper(client=MagicMock()).run({"city": "Shanghai", "horizon": 7})


def test_demand_wrapper_propagates_hf_errors() -> None:
    mock_client = MagicMock()
    mock_client.predict_demand.side_effect = RuntimeError("HF Space unavailable")

    with pytest.raises(RuntimeError, match="HF Space unavailable"):
        DemandWrapper(client=mock_client).run(CONTEXT_PAYLOAD)
