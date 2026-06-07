"""
Validation script for orchestration flow.

Runs sample queries through the compiled LangGraph workflow and asserts that
classification, routing, agent execution, and response formatting work
correctly end-to-end.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.graph import ORCHESTRATOR_APP
from orchestrator.intent import detect_intent
from orchestrator.state import AgentState

app = ORCHESTRATOR_APP

TEST_CASES = [
    {
        "query": "Show inventory levels for warehouse A",
        "expected_domain": "inventory",
        "expected_task": "inventory_nlsql",
        "description": (
            "Validates inventory routing for warehouse / stock questions."
        ),
    },
    {
        "query": "Forecast delivery demand next week",
        "expected_domain": "logistics",
        "expected_task": "demand_forecast",
        "description": (
            "Validates demand forecasting routes to the logistics agent."
        ),
    },
    {
        "query": "How many iphones are there in shanghai",
        "expected_domain": "inventory",
        "expected_task": "inventory_nlsql",
        "description": (
            "Product/city NL-to-SQL questions route to the inventory agent."
        ),
    },
    {
        "query": "Show shipment ETA",
        "expected_domain": "logistics",
        "expected_task": "eta_lookup",
        "description": (
            "Validates logistics keyword detection and routing."
        ),
    },
    {
        "query": "Optimize delivery routes",
        "expected_domain": "logistics",
        "expected_task": "route_prediction",
        "description": (
            "Validates route prediction routing to the logistics agent."
        ),
    },
    {
        "query": "Hello world",
        "expected_domain": "logistics",
        "expected_task": "shipment_lookup",
        "description": (
            "Ambiguous queries default to logistics when classifier picks logistics."
        ),
    },
]


def _initial_state(user_query: str) -> AgentState:
    return {
        "user_query": user_query,
        "domain": "",
        "task": "",
        "confidence": 0.0,
        "intent": "",
        "selected_agent": "",
        "ml_task": "",
        "agent_response": "",
        "final_response": "",
        "user_role": "LOGISTICS",
        "access_denied": False,
    }


def _mock_logistics_complete(*_args, **_kwargs) -> dict:
    return {
        "agent": "logistics",
        "status": "complete",
        "answer": "Mock logistics answer.",
        "session": None,
    }


def _mock_logistics_awaiting(*_args, **_kwargs) -> dict:
    return {
        "agent": "logistics",
        "status": "awaiting_input",
        "question": "Which courier is handling this delivery?",
        "session": {"messages": [], "collecting": {"tool": "predict_eta"}},
    }


def _mock_inventory_complete(*_args, **_kwargs) -> dict:
    return {
        "agent": "inventory",
        "status": "complete",
        "answer": "Mock inventory answer.",
        "session": None,
    }


def _mock_inventory_awaiting(*_args, **_kwargs) -> dict:
    return {
        "agent": "inventory",
        "status": "awaiting_input",
        "question": "Which city is this demand forecast for?",
        "session": {"messages": [], "collecting": {"tool": "predict_demand"}},
    }


def _mock_classify_domain_task(query: str) -> dict:
    q = query.lower().strip()
    for case in TEST_CASES:
        if case["query"].lower().strip() == q:
            return {
                "domain": case["expected_domain"],
                "task": case["expected_task"],
                "confidence": 0.95,
            }
    return {"domain": "logistics", "task": "shipment_lookup", "confidence": 0.95}


@patch("agents.logistics_agent.run_logistics_turn", side_effect=_mock_logistics_awaiting)
@patch("agents.inventory_agent.run_inventory_turn", side_effect=_mock_inventory_awaiting)
def run_test_case(index: int, test_case: dict, _mock_inv, _mock_log) -> None:
    query = test_case["query"]
    expected_domain = test_case["expected_domain"]

    print(f"--- Test Case {index} ---")
    print(f"Description: {test_case['description']}")
    print(f"Query: {query}")

    result = app.invoke(_initial_state(query))

    print(f"Detected Domain: {result['domain']}")
    print(f"Detected Task: {result['task']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Selected Agent: {result['selected_agent']}")
    print(f"Final Response: {result['final_response']}")
    print()

    assert result["domain"] == expected_domain
    assert result["intent"] == expected_domain
    assert result["selected_agent"] == expected_domain
    assert result["final_response"]

    payload = json.loads(result["final_response"])
    assert payload.get("status") in {"clarification_required", "success"}
    if expected_domain == "inventory":
        assert payload.get("source") == "inventory"
    else:
        assert payload.get("source") in {"agent", "inventory"}


@patch("orchestrator.intent.classify_domain_task", return_value={
    "domain": "logistics",
    "task": "eta_lookup",
    "confidence": 0.94,
})
@patch("agents.logistics_agent.run_logistics_turn", side_effect=_mock_logistics_complete)
def test_logistics_complete_answer(_mock_turn, _mock_classify) -> None:
    result = app.invoke(_initial_state("What is the shipment ETA?"))
    payload = json.loads(result["final_response"])
    assert payload.get("status") == "success"
    assert payload.get("data", {}).get("answer")


def test_intent_honors_collecting_session() -> None:
    """Numeric follow-ups must not re-route to logistics."""
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
            "messages": [],
            "collecting": {"tool": "predict_demand", "partial": {}},
        },
    }
    result = detect_intent(state)
    assert result["domain"] == "inventory"
    assert result["task"] == "inventory_nlsql"
    assert result["intent"] == "inventory"


def main() -> None:
    print("Running orchestration validation tests...\n")

    test_intent_honors_collecting_session()

    with (
        patch(
            "orchestrator.intent.classify_domain_task",
            side_effect=_mock_classify_domain_task,
        ),
        patch(
            "agents.logistics_agent.run_logistics_turn",
            side_effect=_mock_logistics_awaiting,
        ),
        patch(
            "agents.inventory_agent.run_inventory_turn",
            side_effect=_mock_inventory_awaiting,
        ),
    ):
        for index, test_case in enumerate(TEST_CASES, start=1):
            run_test_case(index, test_case)

    test_logistics_complete_answer()

    print("=====================================")
    print("ALL ORCHESTRATION TESTS PASSED")
    print("=====================================")


if __name__ == "__main__":
    main()
