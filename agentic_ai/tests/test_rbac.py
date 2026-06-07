"""Unit tests for role-based access control."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.graph import ORCHESTRATOR_APP, run_orchestrator
from orchestrator.rbac.exceptions import (
    UnauthorizedTaskError,
    UnknownRoleError,
    UnknownTaskError,
)
from orchestrator.rbac.permissions import ALL_TASKS, ROLE_PERMISSIONS
from orchestrator.rbac.rbac_service import RBACService
from orchestrator.rbac_node import enforce_rbac
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
        "access_denied": False,
    }
    state.update(extra)
    return state


@pytest.fixture
def service() -> RBACService:
    return RBACService()


def test_validate_role_accepts_known_roles(service: RBACService) -> None:
    assert service.validate_role("admin") == "ADMIN"
    assert service.validate_role("LOGISTICS") == "LOGISTICS"


def test_validate_role_rejects_unknown(service: RBACService) -> None:
    with pytest.raises(UnknownRoleError):
        service.validate_role("GUEST")


def test_validate_task_accepts_known_tasks(service: RBACService) -> None:
    assert service.validate_task("ETA_PREDICTION") == "eta_prediction"


def test_validate_task_rejects_unknown(service: RBACService) -> None:
    with pytest.raises(UnknownTaskError):
        service.validate_task("delete_everything")


def test_admin_has_all_tasks(service: RBACService) -> None:
    assert ROLE_PERMISSIONS["ADMIN"] == ALL_TASKS
    for task in ALL_TASKS:
        assert service.check_access("ADMIN", task) is True


def test_inventory_denied_eta_prediction(service: RBACService) -> None:
    assert service.check_access("INVENTORY", "eta_prediction") is False


def test_logistics_allowed_eta_prediction(service: RBACService) -> None:
    assert service.check_access("LOGISTICS", "eta_prediction") is True


def test_courier_allowed_route_prediction(service: RBACService) -> None:
    assert service.check_access("COURIER", "route_prediction") is True


def test_courier_denied_inventory_nlsql(service: RBACService) -> None:
    assert service.check_access("COURIER", "inventory_nlsql") is False


def test_inventory_allowed_inventory_nlsql(service: RBACService) -> None:
    assert service.check_access("INVENTORY", "inventory_nlsql") is True


def test_logistics_denied_inventory_nlsql(service: RBACService) -> None:
    assert service.check_access("LOGISTICS", "inventory_nlsql") is False


def test_require_access_raises_on_deny(service: RBACService) -> None:
    with pytest.raises(UnauthorizedTaskError, match="INVENTORY"):
        service.require_access("INVENTORY", "eta_prediction")


def test_denial_reason_format(service: RBACService) -> None:
    reason = service.denial_reason("INVENTORY", "eta_prediction")
    assert reason == "Role INVENTORY is not allowed to execute eta_prediction"


def test_enforce_rbac_allows_authorized_task() -> None:
    result = enforce_rbac(_base_state(user_role="LOGISTICS", task="eta_prediction"))
    assert result["access_denied"] is False
    assert result.get("agent_response", "") == ""


def test_enforce_rbac_denies_unauthorized_task() -> None:
    result = enforce_rbac(_base_state(user_role="INVENTORY", task="eta_prediction"))
    assert result["access_denied"] is True
    payload = json.loads(result["agent_response"])
    assert payload["status"] == "denied"
    assert payload["reason"] == "Role INVENTORY is not allowed to execute eta_prediction"


def test_enforce_rbac_skips_empty_task() -> None:
    result = enforce_rbac(_base_state(task="", user_role="COURIER"))
    assert result["access_denied"] is False


def test_enforce_rbac_denies_missing_role() -> None:
    result = enforce_rbac(_base_state(user_role=None, task="eta_prediction"))
    assert result["access_denied"] is True
    payload = json.loads(result["agent_response"])
    assert payload["reason"] == "User identity not provided"


@patch("orchestrator.intent.classify_domain_task")
@patch("agents.logistics_agent.run_logistics_turn")
def test_orchestrator_denies_before_agent(
    mock_logistics_turn: MagicMock,
    mock_classify: MagicMock,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_prediction",
        "confidence": 0.95,
    }
    result = run_orchestrator(
        "Predict ETA from Hub A to Hub B",
        user_role="INVENTORY",
    )
    payload = json.loads(result["final_response"])
    assert payload["status"] == "access_denied"
    assert "INVENTORY" in payload["message"]
    mock_logistics_turn.assert_not_called()


@patch("orchestrator.intent.classify_domain_task")
@patch("agents.logistics_agent.run_logistics_turn")
def test_orchestrator_allows_authorized_role(
    mock_logistics_turn: MagicMock,
    mock_classify: MagicMock,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_prediction",
        "confidence": 0.95,
    }
    mock_logistics_turn.return_value = {
        "agent": "logistics",
        "status": "complete",
        "answer": "ok",
        "session": None,
    }
    result = run_orchestrator(
        "Predict ETA from Hub A to Hub B",
        user_role="LOGISTICS",
    )
    payload = json.loads(result["final_response"])
    assert result["access_denied"] is False
    # Phase 5: authorized ML tasks stop at context layer (entity clarification here).
    assert payload["status"] == "clarification_required"
    mock_logistics_turn.assert_not_called()


@patch("orchestrator.intent.classify_domain_task")
@patch("agents.inventory_agent.run_inventory_turn")
def test_orchestrator_inventory_role_inventory_task(
    mock_inventory_turn: MagicMock,
    mock_classify: MagicMock,
) -> None:
    mock_classify.return_value = {
        "domain": "inventory",
        "task": "inventory_nlsql",
        "confidence": 0.96,
    }
    mock_inventory_turn.return_value = {
        "agent": "inventory",
        "status": "complete",
        "answer": "42 laptops",
        "session": None,
    }
    result = run_orchestrator(
        "How many laptops are available in Hub 5?",
        user_role="INVENTORY",
    )
    payload = json.loads(result["final_response"])
    assert payload["status"] == "success"
    assert payload["source"] == "inventory"
    mock_inventory_turn.assert_called_once()


@patch("orchestrator.intent.classify_domain_task")
def test_orchestrator_continues_past_intent_for_bypass_task_low_confidence(
    mock_classify: MagicMock,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "shipment_lookup",
        "confidence": 0.45,
    }
    with patch("agents.logistics_agent.run_logistics_turn") as mock_logistics_turn:
        mock_logistics_turn.return_value = {
            "agent": "logistics",
            "status": "complete",
            "answer": "ok",
            "session": None,
        }
        with patch("graph_retrieval.graph_node._retriever") as mock_retriever:
            mock_retriever.retrieve.return_value = {"found": False}
            result = run_orchestrator("shipment 123", user_role="LOGISTICS")
    assert result["confidence"] == 0.45
    assert not result.get("agent_response", "").startswith('{\n  "status": "awaiting_input"')
    mock_logistics_turn.assert_called_once()
