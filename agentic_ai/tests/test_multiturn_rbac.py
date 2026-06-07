"""Tests for RBAC context persistence across multi-turn sessions."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.graph import run_orchestrator
from orchestrator.intent import detect_intent
from orchestrator.rbac.session_context import build_session_for_response
from orchestrator.response_formatter import ResponseFormatter
from orchestrator.state import AgentState


def test_detect_intent_restores_task_from_logistics_session() -> None:
    state: AgentState = {
        "user_query": "ORD123",
        "domain": "",
        "task": "",
        "confidence": 0.0,
        "intent": "",
        "selected_agent": "",
        "ml_task": "",
        "agent_response": "",
        "final_response": "",
        "logistics_session": {
            "collecting": {"tool": "predict_eta"},
            "task": "eta_prediction",
            "user_role": "LOGISTICS",
        },
    }
    result = detect_intent(state)
    assert result["domain"] == "logistics"
    assert result["task"] == "eta_prediction"


def test_detect_intent_restores_task_from_inventory_session() -> None:
    state: AgentState = {
        "user_query": "3",
        "domain": "",
        "task": "",
        "confidence": 0.0,
        "intent": "",
        "selected_agent": "",
        "ml_task": "",
        "agent_response": "",
        "final_response": "",
        "inventory_session": {
            "collecting": {"tool": "predict_demand"},
            "task": "inventory_nlsql",
            "user_role": "INVENTORY",
        },
    }
    result = detect_intent(state)
    assert result["domain"] == "inventory"
    assert result["task"] == "inventory_nlsql"


def test_build_session_for_response_persists_rbac_fields() -> None:
    state: AgentState = {
        "user_query": "Predict route",
        "domain": "logistics",
        "task": "route_prediction",
        "confidence": 0.9,
        "intent": "logistics",
        "selected_agent": "",
        "ml_task": "",
        "agent_response": "",
        "final_response": "",
        "user_role": "COURIER",
        "logistics_session": {
            "courier_id": "C001",
            "collecting": {"tool": "predict_route"},
        },
        "clarification_needed": True,
    }
    session = build_session_for_response(state)
    assert session is not None
    assert session["user_role"] == "COURIER"
    assert session["task"] == "route_prediction"
    assert session["courier_id"] == "C001"
    assert session["collecting"]["tool"] == "predict_route"


def test_clarification_response_embeds_session() -> None:
    state: AgentState = {
        "user_query": "Predict route",
        "domain": "logistics",
        "task": "route_prediction",
        "confidence": 0.9,
        "intent": "logistics",
        "selected_agent": "",
        "ml_task": "",
        "agent_response": "",
        "final_response": "",
        "user_role": "LOGISTICS",
        "clarification_needed": True,
        "clarification_type": "ENTITY",
        "clarification_question": "Which order?",
        "missing_fields": ["order_id"],
    }
    payload = ResponseFormatter().format(state)
    assert payload["status"] == "clarification_required"
    assert payload["data"]["session"]["user_role"] == "LOGISTICS"
    assert payload["data"]["session"]["task"] == "route_prediction"


@patch("orchestrator.intent.classify_domain_task")
def test_multiturn_restores_role_from_session(mock_classify: MagicMock) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_prediction",
        "confidence": 0.95,
    }
    session = {
        "collecting": {"tool": "predict_eta"},
        "task": "eta_prediction",
        "user_role": "LOGISTICS",
    }
    result = run_orchestrator(
        "ORD123",
        logistics_session=session,
    )
    assert result["user_role"] == "LOGISTICS"
    payload = json.loads(result["final_response"])
    assert payload["status"] in {"clarification_required", "success", "access_denied"}
