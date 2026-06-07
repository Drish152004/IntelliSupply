"""Tests for resource RBAC on ML and context resolution paths."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from context.context_node import resolve_context
from orchestrator.ml_node import execute_ml
from orchestrator.resource_rbac import authorize_courier_resource
from orchestrator.state import AgentState


def _ml_state(**extra) -> AgentState:
    state: AgentState = {
        "user_query": "Predict my route",
        "domain": "logistics",
        "task": "route_prediction",
        "confidence": 0.95,
        "intent": "logistics",
        "selected_agent": "",
        "ml_task": "",
        "agent_response": "",
        "final_response": "",
        "user_role": "COURIER",
        "ready_for_ml": True,
        "payload": {"courier_id": "C001", "order_id": "ORD1"},
    }
    state.update(extra)
    return state


def test_authorize_courier_resource_denies_unbound_courier() -> None:
    allowed, reason, _entities = authorize_courier_resource(
        _ml_state(logistics_session=None),
    )
    assert allowed is False
    assert reason == "Courier identity not bound"


def test_resolve_context_denies_unbound_courier() -> None:
    result = resolve_context(
        _ml_state(ready_for_ml=False, logistics_session=None),
    )
    assert result["authorization_denied"] is True
    payload = json.loads(result["agent_response"])
    assert payload["status"] == "denied"


def test_execute_ml_denies_unbound_courier() -> None:
    result = execute_ml(_ml_state(logistics_session=None))
    assert result["authorization_denied"] is True
    assert result["execution_status"] == "error"


@patch("orchestrator.ml_node.get_ml_executor")
def test_execute_ml_allowed_with_bound_courier(mock_get_executor: MagicMock) -> None:
    mock_executor = MagicMock()
    mock_outcome = MagicMock()
    mock_outcome.to_state_fields.return_value = {
        "execution_status": "success",
        "prediction_result": {"route": []},
        "prediction_type": "route",
    }
    mock_outcome.to_agent_response.return_value = json.dumps({"status": "prediction_complete"})
    mock_executor.execute.return_value = mock_outcome
    mock_get_executor.return_value = mock_executor

    result = execute_ml(
        _ml_state(logistics_session={"courier_id": "C001"}),
    )
    assert result.get("authorization_denied") is not True
    mock_executor.execute.assert_called_once()
