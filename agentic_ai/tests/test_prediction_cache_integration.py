"""Integration tests for ML prediction caching in the orchestrator pipeline."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent
for path in (str(ROOT), str(REPO_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from cache.prediction_cache_key_builder import PredictionCacheKeyBuilder
from context.graph_resolver import GraphResolver, reset_graph_resolver
from context.resolver import ContextResolver, reset_context_resolver
from graph_retrieval.graph_node import reset_graph_retriever
from ml.ml_executor import MLExecutionOutcome
from orchestrator.cache_node import get_cache_service, reset_cache_service
from orchestrator.graph import run_orchestrator


def _wire_eta_graph_resolver(mock_service: MagicMock) -> None:
    graph_resolver = GraphResolver(graph_service=mock_service)
    reset_graph_resolver(graph_resolver)
    reset_context_resolver(ContextResolver(graph_resolver=graph_resolver))


def _eta_ml_outcome(**result) -> MLExecutionOutcome:
    return MLExecutionOutcome(
        success=True,
        prediction_type="eta",
        model_name="lgbm_eta_model",
        result=result or {"eta_minutes": 55.0},
        duration_ms=12.0,
    )


def _route_ml_outcome(**result) -> MLExecutionOutcome:
    return MLExecutionOutcome(
        success=True,
        prediction_type="route",
        model_name="route_model",
        result=result or {"predicted_sequence": ["ORD1", "ORD2"]},
        duration_ms=15.0,
    )


def _demand_ml_outcome(**result) -> MLExecutionOutcome:
    return MLExecutionOutcome(
        success=True,
        prediction_type="demand_forecast",
        model_name="demand_model",
        result=result or {"by_city": [{"city": "Bangalore", "forecast": [1, 2, 3]}]},
        duration_ms=20.0,
    )


@pytest.fixture(autouse=True)
def _reset_services() -> None:
    reset_cache_service()
    reset_graph_retriever()
    reset_graph_resolver()
    reset_context_resolver()
    yield
    reset_cache_service()
    reset_graph_retriever()
    reset_graph_resolver()
    reset_context_resolver()


@patch("orchestrator.intent.classify_domain_task")
@patch("graph_retrieval.graph_node._retriever")
@patch("orchestrator.ml_node.get_ml_executor")
def test_eta_prediction_miss_executes_then_second_request_hits_cache(
    mock_get_executor,
    mock_retriever,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_prediction",
        "confidence": 0.95,
    }
    mock_retriever.retrieve.return_value = {"found": False}
    mock_executor = MagicMock()
    mock_executor.execute.return_value = _eta_ml_outcome(eta_minutes=55.0)
    mock_get_executor.return_value = mock_executor

    mock_service = MagicMock()
    mock_service.execute.return_value = [
        {
            "delivery_user_id": "C001",
            "from_dipan_id": "42",
            "aoi_id": "7",
            "receipt_lat": 30.6,
            "receipt_lng": 104.0,
            "poi_lat": 30.61,
            "poi_lng": 104.01,
            "receipt_time": "2026-06-05T12:00:00",
        }
    ]
    _wire_eta_graph_resolver(mock_service)

    first = run_orchestrator("Predict ETA for order ORD123", user_role="LOGISTICS")
    assert first["graph_hit"] is False
    assert first["prediction_cache_hit"] is False
    assert first["execution_status"] == "success"
    assert mock_executor.execute.call_count == 1
    assert get_cache_service().get("eta_prediction:ORD123") is not None

    second = run_orchestrator("Predict ETA for order ORD123", user_role="LOGISTICS")
    assert second["graph_hit"] is False
    assert second["prediction_cache_hit"] is True
    assert mock_executor.execute.call_count == 1
    payload = json.loads(second["final_response"])
    assert payload["status"] == "success"
    assert payload["source"] == "cache"
    assert payload["data"]["eta_minutes"] == 55.0


@patch("orchestrator.intent.classify_domain_task")
@patch("graph_retrieval.graph_node._retriever")
@patch("orchestrator.ml_node.get_ml_executor")
def test_route_prediction_miss_executes_then_second_request_hits_cache(
    mock_get_executor,
    mock_retriever,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "route_prediction",
        "confidence": 0.95,
    }
    mock_retriever.retrieve.return_value = {"found": False}
    mock_executor = MagicMock()
    mock_executor.execute.return_value = _route_ml_outcome()
    mock_get_executor.return_value = mock_executor

    mock_service = MagicMock()
    mock_service.execute.return_value = [
        {
            "order_id": "ORD123",
            "lat_wgs84": 30.6,
            "lon_wgs84": 104.0,
            "receipt_lat_wgs84": 30.5,
            "receipt_lon_wgs84": 103.9,
            "city_name": "Chongqing",
            "ds": 318,
            "delivery_day": "Monday",
            "receipt_time": "2026-06-05T12:00:00",
            "typecode": "A",
            "aoi_id": "7",
        }
    ]
    _wire_eta_graph_resolver(mock_service)

    first = run_orchestrator("Predict route for order ORD123", user_role="LOGISTICS")
    assert first["execution_status"] == "success"
    assert mock_executor.execute.call_count == 1

    second = run_orchestrator("Predict route for order ORD123", user_role="LOGISTICS")
    assert second["prediction_cache_hit"] is True
    assert mock_executor.execute.call_count == 1
    payload = json.loads(second["final_response"])
    assert payload["source"] == "cache"


@patch("orchestrator.intent.classify_domain_task")
@patch("graph_retrieval.graph_node._retriever")
@patch("orchestrator.ml_node.get_ml_executor")
def test_demand_forecast_miss_executes_then_second_request_hits_cache(
    mock_get_executor,
    mock_retriever,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "demand_forecast",
        "confidence": 0.95,
    }
    mock_retriever.retrieve.return_value = {"found": False}
    mock_executor = MagicMock()
    mock_executor.execute.return_value = _demand_ml_outcome()
    mock_get_executor.return_value = mock_executor

    first = run_orchestrator(
        "Forecast demand for Bangalore",
        user_role="LOGISTICS",
        ml_payload_partial={"horizon": "7"},
    )
    assert first["execution_status"] == "success"
    assert mock_executor.execute.call_count == 1
    key = PredictionCacheKeyBuilder.build(
        "demand_forecast",
        entities=first.get("entities") or {},
        payload=first.get("payload") or {},
    )
    assert key == "demand_forecast:BANGALORE:7"

    second = run_orchestrator(
        "Forecast demand for Bangalore",
        user_role="LOGISTICS",
        ml_payload_partial={"horizon": "7"},
    )
    assert second["prediction_cache_hit"] is True
    assert mock_executor.execute.call_count == 1
    payload = json.loads(second["final_response"])
    assert payload["source"] == "cache"


@patch("orchestrator.intent.classify_domain_task")
@patch("graph_retrieval.graph_node._retriever")
@patch("orchestrator.ml_node.get_ml_executor")
def test_graph_hit_skips_prediction_cache(
    mock_get_executor,
    mock_retriever,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_lookup",
        "confidence": 0.95,
    }
    mock_retriever.retrieve.return_value = {
        "found": True,
        "result": {"order_id": "ORD123", "eta_minutes": 28},
    }
    mock_get_executor.return_value = MagicMock()

    service = get_cache_service()
    service.set(
        "eta_prediction:ORD123",
        {"prediction_type": "eta", "model_name": "x", "result": {"eta_minutes": 99.0}},
        ttl=300,
    )

    result = run_orchestrator("What is ETA for order ORD123?", user_role="LOGISTICS")
    assert result["graph_hit"] is True
    assert result.get("prediction_cache_hit") is not True
    mock_get_executor.return_value.execute.assert_not_called()


@patch("orchestrator.intent.classify_domain_task")
@patch("graph_retrieval.graph_node._retriever")
@patch("orchestrator.ml_node.get_ml_executor")
def test_clarification_required_skips_prediction_cache(
    mock_get_executor,
    mock_retriever,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_prediction",
        "confidence": 0.95,
    }
    mock_retriever.retrieve.return_value = {"found": False}
    mock_get_executor.return_value = MagicMock()

    service = get_cache_service()
    service.set(
        "eta_prediction:ORD123",
        {"prediction_type": "eta", "model_name": "x", "result": {"eta_minutes": 99.0}},
        ttl=300,
    )

    result = run_orchestrator("Predict ETA", user_role="LOGISTICS")
    assert result["clarification_needed"] is True
    assert result.get("prediction_cache_hit") is not True
    mock_get_executor.return_value.execute.assert_not_called()


@patch("orchestrator.intent.classify_domain_task")
@patch("graph_retrieval.graph_node._retriever")
@patch("orchestrator.ml_node.get_ml_executor")
def test_access_denied_skips_prediction_cache(
    mock_get_executor,
    mock_retriever,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_prediction",
        "confidence": 0.95,
    }
    mock_retriever.retrieve.return_value = {"found": False}
    mock_get_executor.return_value = MagicMock()

    service = get_cache_service()
    service.set(
        "eta_prediction:ORD123",
        {"prediction_type": "eta", "model_name": "x", "result": {"eta_minutes": 99.0}},
        ttl=300,
    )

    result = run_orchestrator(
        "Predict ETA for order ORD123",
        user_role="INVENTORY",
    )
    assert result["access_denied"] is True
    assert result.get("prediction_cache_hit") is not True
    mock_get_executor.return_value.execute.assert_not_called()
