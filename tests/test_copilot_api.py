"""Tests for the Copilot testing API."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parent.parent
FASTAPI_ROOT = REPO_ROOT / "FastAPI"
AGENTIC_ROOT = REPO_ROOT / "agentic_ai"

for path in (str(AGENTIC_ROOT), str(REPO_ROOT)):
    if path not in sys.path:
        sys.path.append(path)
if str(FASTAPI_ROOT) not in sys.path:
    sys.path.insert(0, str(FASTAPI_ROOT))

import bootstrap  # noqa: F401 — path setup

from orchestrator.response_formatter import ResponseFormatter
from orchestrator.state import AgentState


def _base_state(**extra: Any) -> AgentState:
    state: AgentState = {
        "user_query": "test",
        "domain": "logistics",
        "task": "eta_prediction",
        "confidence": 0.95,
        "intent": "logistics",
        "selected_agent": "",
        "ml_task": "",
        "agent_response": "",
        "final_response": "",
        "user_role": "LOGISTICS",
    }
    state.update(extra)
    return state


def _orchestrator_result(**extra: Any) -> AgentState:
    state = _base_state(**extra)
    formatter = ResponseFormatter()
    state["final_response"] = formatter.serialize(state)
    return state


@pytest.fixture
def client() -> TestClient:
    from main import app

    return TestClient(app)


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/copilot/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@patch("intellisupply_copilot.copilot_router.run_orchestrator")
def test_inventory_query(mock_run: patch, client: TestClient) -> None:
    mock_run.return_value = _orchestrator_result(
        domain="inventory",
        intent="inventory",
        task="inventory_query",
        user_role="INVENTORY",
        agent_response=json.dumps(
            {
                "status": "success",
                "answer": "Inventory results",
                "result": {"city": "Bangalore", "total_units": 1200},
            }
        ),
    )

    response = client.post(
        "/copilot/query",
        json={
            "query": "Show inventory in Bangalore",
            "authenticated_user": {"role": "inventory_manager"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["data"]["result"]["city"] == "Bangalore"
    mock_run.assert_called_once_with(
        "Show inventory in Bangalore",
        logistics_session=None,
        authenticated_user={"role": "inventory_manager"},
    )


@patch("intellisupply_copilot.copilot_router.run_orchestrator")
def test_eta_prediction(mock_run: patch, client: TestClient) -> None:
    mock_run.return_value = _orchestrator_result(
        task="eta_prediction",
        execution_status="success",
        prediction_type="eta",
        prediction_result={"eta_minutes": 42.5},
        model_name="lgbm_eta_model",
        model_execution_time_ms=15.2,
    )

    response = client.post(
        "/copilot/query",
        json={
            "query": "Predict ETA for order ORD123",
            "authenticated_user": {"role": "logistics_manager"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["source"] == "ml"
    assert payload["task"] == "eta_prediction"
    assert payload["data"]["eta_minutes"] == 42.5


@patch("intellisupply_copilot.copilot_router.run_orchestrator")
def test_route_prediction(mock_run: patch, client: TestClient) -> None:
    mock_run.return_value = _orchestrator_result(
        task="route_prediction",
        execution_status="success",
        prediction_type="route",
        prediction_result={"route_id": "R-99", "stops": 5},
        model_name="route_model",
        model_execution_time_ms=22.0,
    )

    response = client.post(
        "/copilot/query",
        json={"query": "Generate route for order ORD123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["source"] == "ml"
    assert payload["task"] == "route_prediction"
    assert payload["data"]["route_id"] == "R-99"


@patch("intellisupply_copilot.copilot_router.run_orchestrator")
def test_courier_rbac(mock_run: patch, client: TestClient) -> None:
    mock_run.return_value = _orchestrator_result(
        task="route_lookup",
        user_role="COURIER",
        graph_hit=True,
        graph_result={"courier_id": "C001", "route_id": "R-12"},
    )

    response = client.post(
        "/copilot/query",
        json={
            "query": "Show my route",
            "authenticated_user": {"role": "courier", "courier_id": "C001"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["source"] == "graph"
    assert payload["data"]["courier_id"] == "C001"
    mock_run.assert_called_once_with(
        "Show my route",
        logistics_session=None,
        authenticated_user={"role": "courier", "courier_id": "C001"},
    )


@patch("intellisupply_copilot.copilot_router.run_orchestrator")
def test_access_denied(mock_run: patch, client: TestClient) -> None:
    mock_run.return_value = _orchestrator_result(
        task="eta_prediction",
        user_role="INVENTORY",
        access_denied=True,
        agent_response=json.dumps(
            {
                "status": "access_denied",
                "reason": "Role INVENTORY is not allowed to execute eta_prediction",
            }
        ),
    )

    response = client.post(
        "/copilot/query",
        json={
            "query": "Predict ETA for order ORD123",
            "authenticated_user": {"role": "inventory_manager"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "access_denied"
    assert payload["role"] == "INVENTORY"
    assert payload["task"] == "eta_prediction"


@patch("intellisupply_copilot.copilot_router.run_orchestrator")
def test_debug_endpoint(mock_run: patch, client: TestClient) -> None:
    mock_run.return_value = _orchestrator_result(
        intent="logistics",
        task="eta_prediction",
        cache_hit=False,
        graph_hit=False,
        ready_for_ml=True,
        execution_status="success",
        prediction_type="eta",
        prediction_result={"eta_minutes": 30.0},
        model_name="lgbm_eta_model",
        model_execution_time_ms=12.0,
    )

    response = client.post(
        "/copilot/debug",
        json={"query": "Predict ETA for order ORD123"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "logistics"
    assert payload["task"] == "eta_prediction"
    assert payload["cache_hit"] is False
    assert payload["graph_hit"] is False
    assert payload["ready_for_ml"] is True
    assert payload["prediction_result"]["eta_minutes"] == 30.0
    assert payload["final_response"]["status"] == "success"
    assert payload["final_response"]["source"] == "ml"


@patch("intellisupply_copilot.copilot_router.run_orchestrator")
def test_query_handles_unhandled_exception(mock_run: patch, client: TestClient) -> None:
    mock_run.side_effect = RuntimeError("Neo4j connection failed")

    response = client.post("/copilot/query", json={"query": "Predict ETA for order ORD123"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "error"
    assert "Neo4j connection failed" in payload["message"]
