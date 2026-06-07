"""Integration tests for Phase 6B ML execution in the orchestrator."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

AGENTIC_ROOT = Path(__file__).resolve().parent.parent / "agentic_ai"
REPO_ROOT = Path(__file__).resolve().parent.parent
for path in (str(AGENTIC_ROOT), str(REPO_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from context.graph_resolver import reset_graph_resolver
from context.resolver import reset_context_resolver
from graph_retrieval.graph_node import reset_graph_retriever
from ml.ml_executor import MLExecutionOutcome, reset_ml_executor
from orchestrator.cache_node import reset_cache_service
from orchestrator.graph import run_orchestrator
from orchestrator.ml_node import execute_ml
from orchestrator.state import AgentState

ETA_CONTEXT_PAYLOAD = {
    "delivery_user_id": "C001",
    "from_dipan_id": "42",
    "aoi_id": "7",
    "receipt_lat": 30.6,
    "receipt_lng": 104.0,
    "poi_lat": 30.61,
    "poi_lng": 104.01,
    "receipt_time": "2026-06-05T12:00:00",
}

ROUTE_CONTEXT_PAYLOAD = {
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

DEMAND_CONTEXT_PAYLOAD = {
    "city": "Shanghai",
    "horizon": "7",
    "granularity": "daily",
    "dataset_kind": "delivery",
}


def _success_outcome(
    *,
    prediction_type: str,
    model_name: str,
    result: dict,
) -> MLExecutionOutcome:
    return MLExecutionOutcome(
        success=True,
        prediction_type=prediction_type,
        model_name=model_name,
        result=result,
        duration_ms=12.5,
    )


def _base_state(**extra) -> AgentState:
    state: AgentState = {
        "user_query": "Predict ETA",
        "domain": "logistics",
        "task": "eta_prediction",
        "confidence": 0.95,
        "intent": "logistics",
        "selected_agent": "",
        "ml_task": "",
        "agent_response": "",
        "final_response": "",
        "user_role": "LOGISTICS",
        "access_denied": False,
        "cache_hit": False,
        "cache_key": None,
        "cached_result": None,
        "entities": {},
        "graph_hit": False,
        "graph_result": None,
        "authorization_denied": False,
        "ready_for_ml": False,
        "payload": None,
        "resolved_context": None,
        "graph_enriched_fields": [],
        "user_supplied_fields": [],
        "missing_fields": [],
        "clarification_needed": False,
        "clarification_type": None,
        "clarification_question": None,
        "prediction_type": None,
        "prediction_result": None,
        "model_name": None,
        "model_execution_time_ms": None,
        "execution_status": None,
        "execution_error": None,
    }
    state.update(extra)
    return state


@pytest.fixture(autouse=True)
def _reset_services() -> None:
    reset_cache_service()
    reset_graph_retriever()
    reset_graph_resolver()
    reset_context_resolver()
    reset_ml_executor()
    yield
    reset_cache_service()
    reset_graph_retriever()
    reset_graph_resolver()
    reset_context_resolver()
    reset_ml_executor()


@patch("orchestrator.ml_node.get_ml_executor")
def test_ml_node_skips_when_not_ready(mock_get_executor) -> None:
    result = execute_ml(_base_state(ready_for_ml=False))
    assert result["ready_for_ml"] is False
    mock_get_executor.assert_not_called()


@patch("orchestrator.ml_node.get_ml_executor")
def test_ml_node_executes_when_ready(mock_get_executor) -> None:
    mock_executor = MagicMock()
    mock_executor.execute.return_value = _success_outcome(
        prediction_type="eta",
        model_name="lgbm_eta_model",
        result={"eta_minutes": 40.0},
    )
    mock_get_executor.return_value = mock_executor

    result = execute_ml(
        _base_state(
            ready_for_ml=True,
            payload=ETA_CONTEXT_PAYLOAD,
            task="eta_prediction",
        )
    )

    mock_executor.execute.assert_called_once_with("eta_prediction", ETA_CONTEXT_PAYLOAD)
    assert result["execution_status"] == "success"
    assert result["prediction_type"] == "eta"
    assert result["prediction_result"]["eta_minutes"] == 40.0
    payload = json.loads(result["agent_response"])
    assert payload["status"] == "prediction_complete"


@patch("orchestrator.intent.classify_domain_task")
@patch("agents.logistics_agent.run_logistics_turn")
@patch("graph_retrieval.graph_node._retriever")
@patch("orchestrator.ml_node.get_ml_executor")
def test_orchestrator_eta_executes_wrapper(
    mock_get_executor,
    mock_retriever,
    mock_logistics_turn,
    mock_classify,
) -> None:
    from context.graph_resolver import GraphResolver
    from context.resolver import ContextResolver

    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_prediction",
        "confidence": 0.95,
    }
    mock_retriever.retrieve.return_value = {"found": False}
    mock_executor = MagicMock()
    mock_executor.execute.return_value = _success_outcome(
        prediction_type="eta",
        model_name="lgbm_eta_model",
        result={"eta_minutes": 55.0},
    )
    mock_get_executor.return_value = mock_executor

    mock_service = MagicMock()
    mock_service.execute.return_value = [ETA_CONTEXT_PAYLOAD]
    reset_graph_resolver(GraphResolver(graph_service=mock_service))
    reset_context_resolver(ContextResolver(graph_resolver=GraphResolver(graph_service=mock_service)))

    result = run_orchestrator(
        "Predict ETA for order ORD123",
        user_role="LOGISTICS",
    )

    assert result["ready_for_ml"] is True
    assert result["execution_status"] == "success"
    assert result["prediction_result"]["eta_minutes"] == 55.0
    mock_logistics_turn.assert_not_called()
    mock_executor.execute.assert_called_once()
    payload = json.loads(result["final_response"])
    assert payload["status"] == "success"
    assert payload["source"] == "ml"
    assert payload["data"]["eta_minutes"] == 55.0


@patch("orchestrator.intent.classify_domain_task")
@patch("agents.logistics_agent.run_logistics_turn")
@patch("graph_retrieval.graph_node._retriever")
@patch("orchestrator.ml_node.get_ml_executor")
def test_orchestrator_route_executes_wrapper(
    mock_get_executor,
    mock_retriever,
    mock_logistics_turn,
    mock_classify,
) -> None:
    from context.graph_resolver import GraphResolver
    from context.resolver import ContextResolver

    mock_classify.return_value = {
        "domain": "logistics",
        "task": "route_prediction",
        "confidence": 0.95,
    }
    mock_retriever.retrieve.return_value = {"found": False}
    mock_executor = MagicMock()
    mock_executor.execute.return_value = _success_outcome(
        prediction_type="route",
        model_name="route_ranker",
        result={"orders_processed": 1, "courier_routes": []},
    )
    mock_get_executor.return_value = mock_executor

    mock_service = MagicMock()
    mock_service.execute.return_value = [ROUTE_CONTEXT_PAYLOAD]
    reset_graph_resolver(GraphResolver(graph_service=mock_service))
    reset_context_resolver(ContextResolver(graph_resolver=GraphResolver(graph_service=mock_service)))

    result = run_orchestrator(
        "Generate route for order ORD123",
        user_role="LOGISTICS",
    )

    assert result["execution_status"] == "success"
    assert result["prediction_type"] == "route"
    mock_executor.execute.assert_called_once_with("route_prediction", ROUTE_CONTEXT_PAYLOAD)
    mock_logistics_turn.assert_not_called()


@patch("orchestrator.intent.classify_domain_task")
@patch("agents.inventory_agent_loop.run_inventory_turn")
@patch("graph_retrieval.graph_node._retriever")
@patch("orchestrator.ml_node.get_ml_executor")
def test_orchestrator_demand_executes_wrapper(
    mock_get_executor,
    mock_retriever,
    mock_inventory_turn,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "inventory",
        "task": "demand_forecast",
        "confidence": 0.95,
    }
    mock_retriever.retrieve.return_value = {"found": False}
    mock_executor = MagicMock()
    mock_executor.execute.return_value = _success_outcome(
        prediction_type="demand_forecast",
        model_name="lade_demand_forecaster",
        result={"horizon": 7, "by_city": [{"city": "Shanghai", "predicted_demand": 1000}]},
    )
    mock_get_executor.return_value = mock_executor

    result = run_orchestrator(
        "Forecast delivery demand in Shanghai for next 7 days",
        user_role="ADMIN",
    )

    assert result["execution_status"] == "success"
    assert result["prediction_type"] == "demand_forecast"
    mock_executor.execute.assert_called_once()
    mock_inventory_turn.assert_not_called()


@patch("orchestrator.intent.classify_domain_task")
@patch("orchestrator.ml_node.get_ml_executor")
def test_orchestrator_graph_hit_skips_ml(
    mock_get_executor,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_lookup",
        "confidence": 0.95,
    }
    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = {
        "found": True,
        "result": {"answer": "ETA is 30 minutes."},
    }
    reset_graph_retriever(mock_retriever)

    result = run_orchestrator(
        "What is the ETA for order ORD123?",
        user_role="LOGISTICS",
    )

    assert result["graph_hit"] is True
    mock_get_executor.assert_not_called()
    assert result.get("execution_status") is None


@patch("orchestrator.intent.classify_domain_task")
@patch("orchestrator.ml_node.get_ml_executor")
@patch("graph_retrieval.graph_node._retriever")
def test_orchestrator_clarification_skips_ml(
    mock_retriever,
    mock_get_executor,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_prediction",
        "confidence": 0.95,
    }
    mock_retriever.retrieve.return_value = {"found": False}

    result = run_orchestrator("Predict ETA", user_role="LOGISTICS")

    assert result["clarification_needed"] is True
    mock_get_executor.assert_not_called()
    assert result.get("execution_status") is None
    payload = json.loads(result["final_response"])
    assert payload["status"] == "clarification_required"
