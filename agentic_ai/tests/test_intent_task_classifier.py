"""Tests for domain/task classification."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.graph import ORCHESTRATOR_APP, run_orchestrator
from orchestrator.intent import detect_intent
from orchestrator.intent_task_classifier import (
    CONFIDENCE_THRESHOLD,
    _keyword_fallback,
    _normalize_result,
    _parse_classifier_response,
    build_clarification_question,
    classify_domain_task,
)
from orchestrator.state import AgentState


def _base_state(user_query: str, **extra) -> AgentState:
    state: AgentState = {
        "user_query": user_query,
        "domain": "",
        "task": "",
        "confidence": 0.0,
        "intent": "",
        "selected_agent": "",
        "ml_task": "",
        "agent_response": "",
        "final_response": "",
    }
    state.update(extra)
    return state


def _mock_llm_response(payload: dict) -> MagicMock:
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps(payload)
    return mock_response


def test_parse_classifier_response() -> None:
    raw = '{"domain": "inventory", "task": "inventory_nlsql", "confidence": 0.96}'
    parsed = _parse_classifier_response(raw)
    assert parsed == {
        "domain": "inventory",
        "task": "inventory_nlsql",
        "confidence": 0.96,
    }


def test_normalize_result_rejects_invalid_domain_task_pair() -> None:
    assert _normalize_result(
        {"domain": "inventory", "task": "eta_lookup", "confidence": 0.9}
    ) is None


@patch("orchestrator.intent_task_classifier.get_client")
def test_classify_inventory_nlsql(mock_get_client: MagicMock) -> None:
    mock_get_client.return_value.chat.completions.create.return_value = _mock_llm_response(
        {"domain": "inventory", "task": "inventory_nlsql", "confidence": 0.96}
    )
    result = classify_domain_task("How many laptops are available in Hub 5?")
    assert result["domain"] == "inventory"
    assert result["task"] == "inventory_nlsql"
    assert result["confidence"] >= CONFIDENCE_THRESHOLD


@patch("orchestrator.intent_task_classifier.get_client")
def test_classify_demand_forecast(mock_get_client: MagicMock) -> None:
    mock_get_client.return_value.chat.completions.create.return_value = _mock_llm_response(
        {"domain": "logistics", "task": "demand_forecast", "confidence": 0.95}
    )
    result = classify_domain_task("Forecast delivery demand next week")
    assert result["domain"] == "logistics"
    assert result["task"] == "demand_forecast"


@patch("orchestrator.intent_task_classifier.get_client")
def test_classify_eta_lookup(mock_get_client: MagicMock) -> None:
    mock_get_client.return_value.chat.completions.create.return_value = _mock_llm_response(
        {"domain": "logistics", "task": "eta_lookup", "confidence": 0.94}
    )
    result = classify_domain_task("What is the ETA for order O123?")
    assert result["domain"] == "logistics"
    assert result["task"] == "eta_lookup"


@patch("orchestrator.intent_task_classifier.get_client")
def test_classify_eta_prediction(mock_get_client: MagicMock) -> None:
    mock_get_client.return_value.chat.completions.create.return_value = _mock_llm_response(
        {"domain": "logistics", "task": "eta_prediction", "confidence": 0.93}
    )
    result = classify_domain_task("Predict ETA from Hub A to Hub B")
    assert result["domain"] == "logistics"
    assert result["task"] == "eta_prediction"


@patch("orchestrator.intent_task_classifier.get_client")
def test_classify_route_lookup(mock_get_client: MagicMock) -> None:
    mock_get_client.return_value.chat.completions.create.return_value = _mock_llm_response(
        {"domain": "logistics", "task": "route_lookup", "confidence": 0.91}
    )
    result = classify_domain_task("What route was predicted for order O123?")
    assert result["domain"] == "logistics"
    assert result["task"] == "route_lookup"


@patch("orchestrator.intent_task_classifier.get_client")
def test_classify_route_prediction(mock_get_client: MagicMock) -> None:
    mock_get_client.return_value.chat.completions.create.return_value = _mock_llm_response(
        {"domain": "logistics", "task": "route_prediction", "confidence": 0.92}
    )
    result = classify_domain_task("Predict route for order O123")
    assert result["domain"] == "logistics"
    assert result["task"] == "route_prediction"


@patch("orchestrator.intent_task_classifier.get_client")
def test_classify_shipment_lookup(mock_get_client: MagicMock) -> None:
    mock_get_client.return_value.chat.completions.create.return_value = _mock_llm_response(
        {"domain": "logistics", "task": "shipment_lookup", "confidence": 0.93}
    )
    result = classify_domain_task("Where is shipment SH123?")
    assert result["domain"] == "logistics"
    assert result["task"] == "shipment_lookup"


@patch("orchestrator.intent_task_classifier.get_client")
def test_classify_courier_lookup(mock_get_client: MagicMock) -> None:
    mock_get_client.return_value.chat.completions.create.return_value = _mock_llm_response(
        {"domain": "logistics", "task": "courier_lookup", "confidence": 0.92}
    )
    result = classify_domain_task("Which hub is courier 55 assigned to?")
    assert result["domain"] == "logistics"
    assert result["task"] == "courier_lookup"


@patch("orchestrator.intent_task_classifier.get_client")
def test_classify_next_stop_prediction(mock_get_client: MagicMock) -> None:
    mock_get_client.return_value.chat.completions.create.return_value = _mock_llm_response(
        {"domain": "logistics", "task": "next_stop_prediction", "confidence": 0.90}
    )
    result = classify_domain_task("What is courier 55's next stop?")
    assert result["domain"] == "logistics"
    assert result["task"] == "next_stop_prediction"


@patch("orchestrator.intent_task_classifier.get_client")
def test_low_confidence_clarification(mock_get_client: MagicMock) -> None:
    mock_get_client.return_value.chat.completions.create.return_value = _mock_llm_response(
        {"domain": "logistics", "task": "shipment_lookup", "confidence": 0.45}
    )
    result = detect_intent(_base_state("shipment 123"))
    assert result["confidence"] < CONFIDENCE_THRESHOLD
    payload = json.loads(result["agent_response"])
    assert payload["status"] == "awaiting_input"
    assert "shipment status" in payload["question"].lower()


def test_keyword_fallback_low_confidence_shipment() -> None:
    result = _keyword_fallback("shipment 123")
    assert result["domain"] == "logistics"
    assert result["confidence"] < CONFIDENCE_THRESHOLD


def test_build_clarification_question_shipment() -> None:
    question = build_clarification_question("shipment 123")
    assert "shipment status" in question.lower()
    assert "eta" in question.lower()


def test_detect_intent_inventory_session_continuation() -> None:
    state = _base_state(
        "3",
        inventory_session={
            "messages": [],
            "collecting": {"tool": "predict_demand", "partial": {}},
        },
    )
    result = detect_intent(state)
    assert result["domain"] == "inventory"
    assert result["task"] == "inventory_nlsql"
    assert result["intent"] == "inventory"
    assert result["confidence"] == 1.0


def test_detect_intent_logistics_session_continuation() -> None:
    state = _base_state(
        "55",
        task="eta_prediction",
        logistics_session={
            "messages": [],
            "collecting": {"tool": "predict_eta", "partial": {}},
        },
    )
    result = detect_intent(state)
    assert result["domain"] == "logistics"
    assert result["task"] == "eta_prediction"
    assert result["confidence"] == 1.0


@patch("orchestrator.intent_task_classifier.get_client")
@patch("agents.logistics_agent.run_logistics_turn")
@patch("agents.inventory_agent.run_inventory_turn")
def test_orchestrator_skips_agent_on_low_confidence(
    mock_inventory_turn: MagicMock,
    mock_logistics_turn: MagicMock,
    mock_get_client: MagicMock,
) -> None:
    mock_get_client.return_value.chat.completions.create.return_value = _mock_llm_response(
        {"domain": "logistics", "task": "shipment_lookup", "confidence": 0.45}
    )
    result = ORCHESTRATOR_APP.invoke(_base_state("shipment 123"))
    payload = json.loads(result["final_response"])
    assert payload["status"] == "clarification_required"
    mock_inventory_turn.assert_not_called()
    mock_logistics_turn.assert_not_called()


@patch("orchestrator.intent.classify_domain_task")
def test_run_orchestrator_initializes_classification_fields(
    mock_classify: MagicMock,
) -> None:
    mock_classify.return_value = {
        "domain": "inventory",
        "task": "inventory_nlsql",
        "confidence": 0.96,
    }
    with patch("agents.inventory_agent.run_inventory_turn") as mock_turn:
        mock_turn.return_value = {
            "agent": "inventory",
            "status": "complete",
            "answer": "ok",
            "session": None,
        }
        result = run_orchestrator(
            "How many laptops are available in Hub 5?",
            user_role="INVENTORY",
        )
    assert result["domain"] == "inventory"
    assert result["task"] == "inventory_nlsql"
    assert result["confidence"] == 0.96
    assert result["intent"] == "inventory"
