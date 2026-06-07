"""Tests for demand forecast pipeline wrapper."""

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

CONTEXT_PAYLOAD = {
    "city": "Shanghai",
    "horizon": "7",
    "granularity": "daily",
    "dataset_kind": "delivery",
}


def _pipeline_result() -> SimpleNamespace:
    return SimpleNamespace(
        granularity="daily",
        horizon=7,
        dataset_kind="delivery",
        strategy="daily",
        panel_rows=1200,
        summary=SimpleNamespace(
            total_predicted=15000.0,
            period_start="2026-06-01",
            period_end="2026-06-07",
            n_regions=42,
            cities=["Shanghai"],
        ),
        by_period=[{"date": "2026-06-01", "predicted_demand": 2000}],
        by_city=[{"city": "Shanghai", "predicted_demand": 15000}],
        top_regions=[{"city": "Shanghai", "region_id": "1", "predicted_demand": 500}],
    )


def test_demand_wrapper_normalizes_prediction() -> None:
    mock_pipeline = MagicMock()
    mock_pipeline.run.return_value = _pipeline_result()

    result = DemandWrapper(pipeline=mock_pipeline).run(CONTEXT_PAYLOAD)

    assert result["prediction_type"] == "demand_forecast"
    assert result["model_name"] == "lade_demand_forecaster"
    assert result["result"]["horizon"] == 7
    assert result["result"]["summary"]["total_predicted"] == 15000.0
    assert result["result"]["by_city"][0]["city"] == "Shanghai"
    mock_pipeline.run.assert_called_once_with(
        granularity="daily",
        horizon=7,
        city="Shanghai",
        dataset_kind="delivery",
        save_outputs=False,
    )


def test_demand_wrapper_propagates_pipeline_errors() -> None:
    mock_pipeline = MagicMock()
    mock_pipeline.run.side_effect = FileNotFoundError("LaDe data missing")

    with pytest.raises(FileNotFoundError, match="LaDe data missing"):
        DemandWrapper(pipeline=mock_pipeline).run(CONTEXT_PAYLOAD)
