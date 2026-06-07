"""Tests for route DeliveryPipeline wrapper."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.wrappers.route_wrapper import RouteWrapper

CONTEXT_PAYLOAD = {
    "order_id": "ord-abc123",
    "lat_wgs84": 30.61,
    "lon_wgs84": 104.01,
    "receipt_lat_wgs84": 30.60,
    "receipt_lon_wgs84": 104.00,
    "city_name": "Shanghai",
    "ds": 318,
    "delivery_day": "Monday",
    "receipt_time": "2026-06-05T12:00:00",
    "typecode": "T1",
    "aoi_id": "7",
}


def _pipeline_result() -> SimpleNamespace:
    return SimpleNamespace(
        orders_processed=1,
        cluster_assignments=[],
        courier_assignments=[],
        courier_routes=[
            SimpleNamespace(
                courier_id="courier-1",
                cluster_id=3,
                city_name="Shanghai",
                ds=318,
                delivery_day="Monday",
                order_ids=["ord-abc123"],
                predicted_sequence=["ord-abc123"],
                stops=[
                    {
                        "sequence": 1,
                        "order_id": "ord-abc123",
                        "lat_wgs84": 30.61,
                        "lon_wgs84": 104.01,
                    }
                ],
            )
        ],
    )


def test_route_wrapper_normalizes_prediction() -> None:
    mock_pipeline = MagicMock()
    mock_pipeline.run.return_value = _pipeline_result()

    result = RouteWrapper(pipeline=mock_pipeline).run(CONTEXT_PAYLOAD)

    assert result["prediction_type"] == "route"
    assert result["model_name"] == "route_ranker"
    assert result["result"]["orders_processed"] == 1
    assert result["result"]["courier_routes"][0]["predicted_sequence"] == ["ord-abc123"]
    mock_pipeline.run.assert_called_once()
    orders_arg = mock_pipeline.run.call_args.args[0]
    assert orders_arg[0]["order_id"] == "ord-abc123"
    assert mock_pipeline.run.call_args.kwargs["save_outputs"] is False


def test_route_wrapper_propagates_pipeline_errors() -> None:
    mock_pipeline = MagicMock()
    mock_pipeline.run.side_effect = RuntimeError("cluster data missing")

    with pytest.raises(RuntimeError, match="cluster data missing"):
        RouteWrapper(pipeline=mock_pipeline).run(CONTEXT_PAYLOAD)
