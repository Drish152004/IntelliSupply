"""
End-to-end validation suite for the IntelliSupply orchestration architecture.

Validates realistic business workflows across:
Intent → RBAC → Cache → Query Completeness → Graph Retrieval →
Context Resolver → ML Execution → Response Formatting

Production code is not modified; external dependencies are mocked.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

AGENTIC_ROOT = Path(__file__).resolve().parent.parent / "agentic_ai"
REPO_ROOT = Path(__file__).resolve().parent.parent
for path in (str(AGENTIC_ROOT), str(REPO_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from context.graph_resolver import GraphResolver, reset_graph_resolver
from context.resolver import ContextResolver, reset_context_resolver
from graph_retrieval.graph_node import reset_graph_retriever
from ml.ml_executor import MLExecutionOutcome, reset_ml_executor
from orchestrator.cache_node import get_cache_service, reset_cache_service
from orchestrator.graph import run_orchestrator
from orchestrator.state import AgentState

# ---------------------------------------------------------------------------
# Shared fixtures and helpers
# ---------------------------------------------------------------------------

ETA_CONTEXT_PAYLOAD: dict[str, Any] = {
    "delivery_user_id": "C001",
    "from_dipan_id": "42",
    "aoi_id": "7",
    "receipt_lat": 30.6,
    "receipt_lng": 104.0,
    "poi_lat": 30.61,
    "poi_lng": 104.01,
    "receipt_time": "2026-06-05T12:00:00",
}

ETA_CONTEXT_MISSING_TIME: dict[str, Any] = {
    k: v for k, v in ETA_CONTEXT_PAYLOAD.items() if k != "receipt_time"
}

ROUTE_CONTEXT_PAYLOAD: dict[str, Any] = {
    "order_id": "ORD123",
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

DEMAND_CONTEXT_PAYLOAD: dict[str, Any] = {
    "city": "Bangalore",
    "horizon": "7",
    "granularity": "daily",
    "dataset_kind": "delivery",
}


def _parse_final(state: AgentState) -> dict[str, Any]:
    return json.loads(state["final_response"])


def _ml_success(
    *,
    prediction_type: str,
    model_name: str,
    result: dict[str, Any],
) -> MLExecutionOutcome:
    return MLExecutionOutcome(
        success=True,
        prediction_type=prediction_type,
        model_name=model_name,
        result=result,
        duration_ms=18.0,
    )


def _ml_failure(message: str = "ETA model execution failed") -> MLExecutionOutcome:
    return MLExecutionOutcome(
        success=False,
        prediction_type=None,
        model_name=None,
        result=None,
        duration_ms=5.0,
        error_message=message,
    )


def _wire_eta_graph_resolver(
    mock_service: MagicMock,
    *,
    payload: dict[str, Any] | None = None,
) -> None:
    mock_service.execute.return_value = [payload or ETA_CONTEXT_PAYLOAD]
    graph_resolver = GraphResolver(graph_service=mock_service)
    reset_graph_resolver(graph_resolver)
    reset_context_resolver(ContextResolver(graph_resolver=graph_resolver))


@pytest.fixture(autouse=True)
def _reset_pipeline_services() -> None:
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


# ---------------------------------------------------------------------------
# TEST 1 — Inventory Query
# ---------------------------------------------------------------------------


@patch("orchestrator.intent.classify_domain_task")
@patch("agents.inventory_agent.run_inventory_turn")
@patch("graph_retrieval.graph_node._retriever")
def test_01_inventory_query_invokes_agent_and_formats_response(
    mock_retriever,
    mock_inventory_turn,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "inventory",
        "task": "inventory_nlsql",
        "confidence": 0.96,
    }
    mock_inventory_turn.return_value = {
        "agent": "inventory",
        "status": "complete",
        "answer": "Bangalore hub has 128 units across 14 SKUs.",
        "session": None,
    }

    result = run_orchestrator(
        "Show inventory in Bangalore",
        user_role="INVENTORY",
    )

    mock_inventory_turn.assert_called_once()
    mock_retriever.retrieve.assert_not_called()

    assert result["domain"] == "inventory"
    assert result["task"] == "inventory_nlsql"
    assert result["selected_agent"] == "inventory"

    response = _parse_final(result)
    assert response["status"] == "success"
    assert response["source"] == "inventory"
    assert "Bangalore" in response["data"]["answer"]


# ---------------------------------------------------------------------------
# TEST 2 — ETA Lookup Graph Hit
# ---------------------------------------------------------------------------


@patch("orchestrator.intent.classify_domain_task")
@patch("orchestrator.ml_node.get_ml_executor")
def test_02_eta_lookup_graph_hit_skips_ml(
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
        "result": {"order_id": "ORD123", "eta_minutes": 28},
    }
    reset_graph_retriever(mock_retriever)

    result = run_orchestrator(
        "What is ETA for order ORD123?",
        user_role="LOGISTICS",
    )

    assert result["graph_hit"] is True
    assert result.get("ready_for_ml") is not True
    mock_get_executor.assert_not_called()
    mock_retriever.retrieve.assert_called_once()

    response = _parse_final(result)
    assert response["status"] == "success"
    assert response["source"] == "graph"
    assert response["data"]["eta_minutes"] == 28


# ---------------------------------------------------------------------------
# TEST 3 — ETA Prediction Full Flow
# ---------------------------------------------------------------------------


@patch("orchestrator.intent.classify_domain_task")
@patch("agents.logistics_agent.run_logistics_turn")
@patch("graph_retrieval.graph_node._retriever")
@patch("orchestrator.ml_node.get_ml_executor")
def test_03_eta_prediction_full_flow(
    mock_get_executor,
    mock_retriever,
    mock_logistics_turn,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_prediction",
        "confidence": 0.95,
    }
    mock_retriever.retrieve.return_value = {"found": False}
    mock_executor = MagicMock()
    mock_executor.execute.return_value = _ml_success(
        prediction_type="eta",
        model_name="lgbm_eta_model",
        result={"eta_minutes": 47.5},
    )
    mock_get_executor.return_value = mock_executor

    mock_service = MagicMock()
    _wire_eta_graph_resolver(mock_service)

    result = run_orchestrator(
        "Predict ETA for order ORD123",
        user_role="LOGISTICS",
    )

    assert result["intent"] == "logistics"
    assert result["task"] == "eta_prediction"
    assert result["cache_hit"] is False
    assert result["graph_hit"] is False
    assert result["ready_for_ml"] is True
    assert result["execution_status"] == "success"
    assert result["prediction_result"]["eta_minutes"] == 47.5

    mock_logistics_turn.assert_not_called()
    mock_executor.execute.assert_called_once_with("eta_prediction", ETA_CONTEXT_PAYLOAD)

    response = _parse_final(result)
    assert response["status"] == "success"
    assert response["source"] == "ml"
    assert response["task"] == "eta_prediction"
    assert response["data"]["eta_minutes"] == 47.5


# ---------------------------------------------------------------------------
# TEST 4 — ETA Prediction HITL #1 (entity clarification)
# ---------------------------------------------------------------------------


@patch("orchestrator.intent.classify_domain_task")
@patch("orchestrator.ml_node.get_ml_executor")
@patch("graph_retrieval.graph_node._retriever")
def test_04_eta_prediction_hitl_entity_clarification(
    mock_retriever,
    mock_get_executor,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_prediction",
        "confidence": 0.95,
    }

    result = run_orchestrator("Predict ETA", user_role="LOGISTICS")

    assert result["clarification_needed"] is True
    assert result["clarification_type"] == "ENTITY"
    mock_retriever.retrieve.assert_not_called()
    mock_get_executor.assert_not_called()

    response = _parse_final(result)
    assert response["status"] == "clarification_required"
    assert response["clarification_type"] == "ENTITY"
    assert response["question"]


# ---------------------------------------------------------------------------
# TEST 5 — ETA Prediction HITL #2 (payload clarification)
# ---------------------------------------------------------------------------


@patch("orchestrator.intent.classify_domain_task")
@patch("orchestrator.ml_node.get_ml_executor")
@patch("graph_retrieval.graph_node._retriever")
def test_05_eta_prediction_hitl_payload_clarification(
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

    mock_service = MagicMock()
    _wire_eta_graph_resolver(mock_service, payload=ETA_CONTEXT_MISSING_TIME)

    result = run_orchestrator(
        "Predict ETA for order ORD123",
        user_role="LOGISTICS",
    )

    assert result["clarification_needed"] is True
    assert result["clarification_type"] == "PAYLOAD"
    assert "receipt_time" in result["missing_fields"]
    mock_get_executor.assert_not_called()

    response = _parse_final(result)
    assert response["status"] == "clarification_required"
    assert response["clarification_type"] == "PAYLOAD"
    assert "receipt_time" in response["missing_fields"]


# ---------------------------------------------------------------------------
# TEST 6 — Route Prediction
# ---------------------------------------------------------------------------


@patch("orchestrator.intent.classify_domain_task")
@patch("agents.logistics_agent.run_logistics_turn")
@patch("graph_retrieval.graph_node._retriever")
@patch("orchestrator.ml_node.get_ml_executor")
def test_06_route_prediction_executes_pipeline(
    mock_get_executor,
    mock_retriever,
    mock_logistics_turn,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "route_prediction",
        "confidence": 0.95,
    }
    mock_retriever.retrieve.return_value = {"found": False}
    mock_executor = MagicMock()
    mock_executor.execute.return_value = _ml_success(
        prediction_type="route",
        model_name="route_ranker",
        result={
            "orders_processed": 1,
            "courier_routes": [
                {
                    "courier_id": "courier-1",
                    "predicted_sequence": ["ORD123"],
                    "stops": [{"order_id": "ORD123", "sequence": 1}],
                }
            ],
        },
    )
    mock_get_executor.return_value = mock_executor

    mock_service = MagicMock()
    mock_service.execute.return_value = [ROUTE_CONTEXT_PAYLOAD]
    _wire_eta_graph_resolver(mock_service, payload=ROUTE_CONTEXT_PAYLOAD)

    result = run_orchestrator(
        "Generate route for order ORD123",
        user_role="LOGISTICS",
    )

    assert result["execution_status"] == "success"
    assert result["prediction_type"] == "route"
    mock_logistics_turn.assert_not_called()
    mock_executor.execute.assert_called_once()

    response = _parse_final(result)
    assert response["status"] == "success"
    assert response["source"] == "ml"
    assert response["task"] == "route_prediction"
    assert response["data"]["orders_processed"] == 1


# ---------------------------------------------------------------------------
# TEST 7 — Demand Forecast
# ---------------------------------------------------------------------------


@patch("orchestrator.intent.classify_domain_task")
@patch("agents.inventory_agent.run_inventory_turn")
@patch("graph_retrieval.graph_node._retriever")
@patch("orchestrator.ml_node.get_ml_executor")
def test_07_demand_forecast_executes_pipeline(
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
    mock_executor = MagicMock()
    mock_executor.execute.return_value = _ml_success(
        prediction_type="demand_forecast",
        model_name="lade_demand_forecaster",
        result={
            "horizon": 7,
            "by_city": [{"city": "Bangalore", "predicted_demand": 2400}],
            "top_regions": [{"city": "Bangalore", "region_id": "12", "predicted_demand": 800}],
        },
    )
    mock_get_executor.return_value = mock_executor

    # Horizon supplied via partial payload (prior turn / defaults collection).
    result = run_orchestrator(
        "Forecast demand for Bangalore",
        user_role="ADMIN",
        ml_payload_partial={"horizon": "7"},
    )

    assert result["ready_for_ml"] is True
    assert result["execution_status"] == "success"
    assert result["prediction_type"] == "demand_forecast"
    mock_inventory_turn.assert_not_called()
    mock_retriever.retrieve.assert_not_called()
    mock_executor.execute.assert_called_once()

    response = _parse_final(result)
    assert response["status"] == "success"
    assert response["source"] == "ml"
    assert response["task"] == "demand_forecast"
    assert response["data"]["by_city"][0]["city"] == "Bangalore"


# ---------------------------------------------------------------------------
# TEST 8 — RBAC Deny
# ---------------------------------------------------------------------------


@patch("orchestrator.intent.classify_domain_task")
@patch("orchestrator.ml_node.get_ml_executor")
@patch("graph_retrieval.graph_node._retriever")
@patch("agents.logistics_agent.run_logistics_turn")
def test_08_rbac_inventory_role_denied_eta_prediction(
    mock_logistics_turn,
    mock_retriever,
    mock_get_executor,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_prediction",
        "confidence": 0.95,
    }

    result = run_orchestrator(
        "Predict ETA for order ORD123",
        user_role="INVENTORY",
    )

    assert result["access_denied"] is True
    mock_retriever.retrieve.assert_not_called()
    mock_get_executor.assert_not_called()
    mock_logistics_turn.assert_not_called()

    response = _parse_final(result)
    assert response["status"] == "access_denied"
    assert response["role"] == "INVENTORY"
    assert response["task"] == "eta_prediction"


# ---------------------------------------------------------------------------
# TEST 9 — Courier Authorization
# ---------------------------------------------------------------------------


@patch("orchestrator.intent.classify_domain_task")
@patch("orchestrator.ml_node.get_ml_executor")
@patch("graph_retrieval.graph_node._retriever")
def test_09_courier_authorization_denied_other_courier_route(
    mock_retriever,
    mock_get_executor,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "route_lookup",
        "confidence": 0.95,
    }

    result = run_orchestrator(
        "Show route for courier C999",
        user_role="COURIER",
        logistics_session={"courier_id": "C001"},
    )

    assert result["authorization_denied"] is True
    assert result["graph_hit"] is False
    mock_get_executor.assert_not_called()
    mock_retriever.retrieve.assert_not_called()

    response = _parse_final(result)
    assert response["status"] == "access_denied"
    assert "C001" in response["message"] or "cannot access" in response["message"].lower()


# ---------------------------------------------------------------------------
# TEST 10 — Cache (miss then hit)
# ---------------------------------------------------------------------------


@patch("orchestrator.intent.classify_domain_task")
@patch("agents.logistics_agent.run_logistics_turn")
@patch("graph_retrieval.graph_node._retriever")
@patch("orchestrator.ml_node.get_ml_executor")
def test_10_cache_second_request_hits_without_graph_or_ml(
    mock_get_executor,
    mock_retriever,
    mock_logistics_turn,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_lookup",
        "confidence": 0.95,
    }
    mock_retriever.retrieve.return_value = {"found": False}
    mock_logistics_turn.return_value = {
        "agent": "logistics",
        "status": "complete",
        "business_result": {"eta_minutes": 36, "order_id": "ORD123"},
    }

    first = run_orchestrator(
        "What is the ETA for order ORD123?",
        user_role="LOGISTICS",
    )
    assert first["cache_hit"] is False
    assert mock_logistics_turn.call_count == 1
    assert mock_retriever.retrieve.call_count == 1
    assert get_cache_service().stats()["stores"] == 1

    second = run_orchestrator(
        "What is the ETA of order ORD123?",
        user_role="LOGISTICS",
    )
    assert second["cache_hit"] is True
    assert mock_logistics_turn.call_count == 1
    assert mock_retriever.retrieve.call_count == 1
    mock_get_executor.assert_not_called()

    response = _parse_final(second)
    assert response["status"] == "success"
    assert response["source"] == "cache"
    assert response["data"]["eta_minutes"] == 36


# ---------------------------------------------------------------------------
# TEST 11 — ML Failure
# ---------------------------------------------------------------------------


@patch("orchestrator.intent.classify_domain_task")
@patch("graph_retrieval.graph_node._retriever")
@patch("orchestrator.ml_node.get_ml_executor")
def test_11_ml_failure_returns_structured_error_without_crash(
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
    mock_executor.execute.return_value = _ml_failure("ETA model execution failed: timeout")
    mock_get_executor.return_value = mock_executor

    mock_service = MagicMock()
    _wire_eta_graph_resolver(mock_service)

    result = run_orchestrator(
        "Predict ETA for order ORD123",
        user_role="LOGISTICS",
    )

    assert result["execution_status"] == "error"
    assert result["execution_error"] is not None
    assert result["prediction_result"] is None

    response = _parse_final(result)
    assert response["status"] == "error"
    assert response["stage"] == "ml_execution"
    assert "failed" in response["message"].lower()


# ---------------------------------------------------------------------------
# TEST 12 — State Validation (full ETA prediction path)
# ---------------------------------------------------------------------------


@patch("orchestrator.intent.classify_domain_task")
@patch("graph_retrieval.graph_node._retriever")
@patch("orchestrator.ml_node.get_ml_executor")
def test_12_state_validation_through_full_eta_prediction(
    mock_get_executor,
    mock_retriever,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_prediction",
        "confidence": 0.94,
    }
    mock_retriever.retrieve.return_value = {"found": False}
    mock_executor = MagicMock()
    mock_executor.execute.return_value = _ml_success(
        prediction_type="eta",
        model_name="lgbm_eta_model",
        result={"eta_minutes": 51.0},
    )
    mock_get_executor.return_value = mock_executor

    mock_service = MagicMock()
    _wire_eta_graph_resolver(mock_service)

    result = run_orchestrator(
        "Predict ETA for order ORD123",
        user_role="LOGISTICS",
    )

    # Intent classification
    assert result["domain"] == "logistics"
    assert result["intent"] == "logistics"
    assert result["task"] == "eta_prediction"
    assert result["confidence"] == pytest.approx(0.94)

    # RBAC / cache / graph
    assert result["access_denied"] is False
    assert result["cache_hit"] is False
    assert result["graph_hit"] is False
    assert result["authorization_denied"] is False

    # Query completeness + context resolver
    assert result["clarification_needed"] is False
    assert result["entities"].get("order_id") == "ORD123"
    assert result["ready_for_ml"] is True
    assert result["payload"] is not None
    assert result["payload"]["delivery_user_id"] == "C001"

    # ML execution
    assert result["execution_status"] == "success"
    assert result["prediction_type"] == "eta"
    assert result["model_name"] == "lgbm_eta_model"
    assert result["prediction_result"]["eta_minutes"] == 51.0
    assert result["model_execution_time_ms"] == pytest.approx(18.0)

    # Response formatting
    response = _parse_final(result)
    assert response["status"] == "success"
    assert response["source"] == "ml"
    assert response["task"] == "eta_prediction"
    assert response["message"]
    assert response["data"]["eta_minutes"] == 51.0
    assert result["final_response"]


# ---------------------------------------------------------------------------
# Architecture coverage summary
# ---------------------------------------------------------------------------

ARCHITECTURE_COVERAGE: dict[str, list[str]] = {
    "Intent Classification": [
        "test_01_inventory_query_invokes_agent_and_formats_response",
        "test_03_eta_prediction_full_flow",
        "test_12_state_validation_through_full_eta_prediction",
    ],
    "RBAC": [
        "test_01_inventory_query_invokes_agent_and_formats_response",
        "test_08_rbac_inventory_role_denied_eta_prediction",
    ],
    "Cache": [
        "test_10_cache_second_request_hits_without_graph_or_ml",
    ],
    "Query Completeness": [
        "test_04_eta_prediction_hitl_entity_clarification",
    ],
    "Graph Retrieval": [
        "test_02_eta_lookup_graph_hit_skips_ml",
        "test_03_eta_prediction_full_flow",
        "test_09_courier_authorization_denied_other_courier_route",
    ],
    "HITL": [
        "test_04_eta_prediction_hitl_entity_clarification",
        "test_05_eta_prediction_hitl_payload_clarification",
    ],
    "Context Resolver": [
        "test_03_eta_prediction_full_flow",
        "test_05_eta_prediction_hitl_payload_clarification",
        "test_06_route_prediction_executes_pipeline",
        "test_07_demand_forecast_executes_pipeline",
        "test_12_state_validation_through_full_eta_prediction",
    ],
    "ML Execution": [
        "test_03_eta_prediction_full_flow",
        "test_06_route_prediction_executes_pipeline",
        "test_07_demand_forecast_executes_pipeline",
        "test_11_ml_failure_returns_structured_error_without_crash",
        "test_12_state_validation_through_full_eta_prediction",
    ],
    "Response Formatting": [
        "test_01_inventory_query_invokes_agent_and_formats_response",
        "test_02_eta_lookup_graph_hit_skips_ml",
        "test_03_eta_prediction_full_flow",
        "test_04_eta_prediction_hitl_entity_clarification",
        "test_05_eta_prediction_hitl_payload_clarification",
        "test_06_route_prediction_executes_pipeline",
        "test_07_demand_forecast_executes_pipeline",
        "test_08_rbac_inventory_role_denied_eta_prediction",
        "test_09_courier_authorization_denied_other_courier_route",
        "test_10_cache_second_request_hits_without_graph_or_ml",
        "test_11_ml_failure_returns_structured_error_without_crash",
        "test_12_state_validation_through_full_eta_prediction",
    ],
}

UNTESTED_EXECUTION_PATHS: list[str] = [
    "Low-confidence intent clarification (confidence below threshold)",
    "shipment_lookup and courier_lookup graph-answer paths",
    "next_stop_prediction ML task",
    "Logistics agent tool-calling loop after graph miss (non-cacheable lookup)",
    "Inventory agent interactive parameter collection (awaiting_input mid-session)",
    "Weekly demand forecast granularity path",
    "Route prediction via from_hub/to_hub entity path (no order_id)",
    "Cache TTL expiration and eviction",
    "Graph persistence of predictions (Phase 7+)",
    "Real Neo4j / sklearn model execution (integration uses mocks)",
]


def test_architecture_coverage_matrix() -> None:
    """Ensure every architectural layer is exercised by this suite."""
    current_tests = {
        name
        for name in globals()
        if name.startswith("test_") and callable(globals()[name])
    }
    for layer, tests in ARCHITECTURE_COVERAGE.items():
        for test_name in tests:
            assert test_name in current_tests, f"{layer} references missing test {test_name}"

    covered_layers = set(ARCHITECTURE_COVERAGE)
    expected_layers = {
        "Intent Classification",
        "RBAC",
        "Cache",
        "Query Completeness",
        "Graph Retrieval",
        "HITL",
        "Context Resolver",
        "ML Execution",
        "Response Formatting",
    }
    assert covered_layers == expected_layers
