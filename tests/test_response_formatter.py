"""Tests for the unified orchestrator response formatter."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

AGENTIC_ROOT = Path(__file__).resolve().parent.parent / "agentic_ai"
if str(AGENTIC_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENTIC_ROOT))

from orchestrator.response_formatter import ResponseFormatter, format_response
from orchestrator.state import AgentState


def _base_state(**extra) -> AgentState:
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


@pytest.fixture
def formatter() -> ResponseFormatter:
    return ResponseFormatter()


def test_format_graph_result(formatter: ResponseFormatter) -> None:
    result = formatter.format(
        _base_state(
            task="eta_lookup",
            graph_hit=True,
            graph_result={"order_id": "ORD123", "eta_minutes": 28},
        )
    )

    assert result["status"] == "success"
    assert result["source"] == "graph"
    assert result["task"] == "eta_lookup"
    assert result["data"]["eta_minutes"] == 28
    assert "knowledge graph" in result["message"].lower()


def test_format_prediction_result(formatter: ResponseFormatter) -> None:
    result = formatter.format(
        _base_state(
            task="eta_prediction",
            execution_status="success",
            prediction_type="eta",
            prediction_result={"eta_minutes": 42.5},
            model_name="lgbm_eta_model",
            model_execution_time_ms=15.2,
        )
    )

    assert result["status"] == "success"
    assert result["source"] == "ml"
    assert result["task"] == "eta_prediction"
    assert result["data"]["eta_minutes"] == 42.5
    assert result["data"]["model_name"] == "lgbm_eta_model"
    assert result["data"]["duration_ms"] == 15.2
    assert "ETA prediction" in result["message"]


def test_format_clarification(formatter: ResponseFormatter) -> None:
    result = formatter.format(
        _base_state(
            task="eta_prediction",
            clarification_needed=True,
            clarification_type="ENTITY",
            clarification_question="Which order should I use?",
            missing_fields=["order_id"],
        )
    )

    assert result["status"] == "clarification_required"
    assert result["clarification_type"] == "ENTITY"
    assert result["question"] == "Which order should I use?"
    assert result["missing_fields"] == ["order_id"]


def test_format_graph_authorization_denied(formatter: ResponseFormatter) -> None:
    result = formatter.format(
        _base_state(
            task="route_lookup",
            user_role="COURIER",
            authorization_denied=True,
            agent_response=json.dumps(
                {
                    "status": "denied",
                    "reason": "Couriers may only access their own route data",
                }
            ),
        )
    )

    assert result["status"] == "access_denied"
    assert result["role"] == "COURIER"
    assert "route" in result["message"].lower() or "authorized" in result["message"].lower()


def test_format_access_denied(formatter: ResponseFormatter) -> None:
    result = formatter.format(
        _base_state(
            task="eta_prediction",
            user_role="INVENTORY",
            access_denied=True,
            agent_response=json.dumps(
                {
                    "status": "denied",
                    "reason": "Role INVENTORY is not allowed to execute eta_prediction",
                }
            ),
        )
    )

    assert result["status"] == "access_denied"
    assert result["role"] == "INVENTORY"
    assert result["task"] == "eta_prediction"
    assert "not allowed" in result["message"]


def test_format_error(formatter: ResponseFormatter) -> None:
    result = formatter.format(
        _base_state(
            task="eta_prediction",
            execution_status="error",
            execution_error="ETA model execution failed: model unavailable",
            agent_response=json.dumps(
                {
                    "status": "error",
                    "stage": "ml_execution",
                    "message": "ETA model execution failed: model unavailable",
                }
            ),
        )
    )

    assert result["status"] == "error"
    assert result["stage"] == "ml_execution"
    assert "model execution failed" in result["message"]
    assert result["details"]["task"] == "eta_prediction"


def test_format_inventory_result(formatter: ResponseFormatter) -> None:
    result = formatter.format(
        _base_state(
            domain="inventory",
            task="inventory_nlsql",
            agent_response=json.dumps(
                {
                    "agent": "inventory",
                    "status": "complete",
                    "answer": "There are 42 units in stock.",
                    "session": None,
                }
            ),
        )
    )

    assert result["status"] == "success"
    assert result["source"] == "inventory"
    assert result["task"] == "inventory_nlsql"
    assert result["data"]["answer"] == "There are 42 units in stock."


def test_format_cache_result(formatter: ResponseFormatter) -> None:
    result = formatter.format(
        _base_state(
            task="eta_lookup",
            cache_hit=True,
            cached_result={"eta_minutes": 30, "order_id": "ORD1"},
            agent_response=json.dumps(
                {
                    "status": "complete",
                    "cached": True,
                    "result": {"eta_minutes": 30, "order_id": "ORD1"},
                }
            ),
        )
    )

    assert result["status"] == "success"
    assert result["source"] == "cache"
    assert result["data"]["eta_minutes"] == 30


def test_format_response_node_sets_final_response() -> None:
    state = format_response(
        _base_state(
            graph_hit=True,
            graph_result={"eta_minutes": 12},
            task="eta_lookup",
        )
    )

    payload = json.loads(state["final_response"])
    assert payload["status"] == "success"
    assert payload["source"] == "graph"
    assert state["final_response"] == state["final_response"]
