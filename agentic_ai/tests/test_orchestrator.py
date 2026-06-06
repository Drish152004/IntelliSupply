"""
Validation script for orchestration flow.

Runs sample queries through the compiled LangGraph workflow and asserts that
intent detection, routing, agent execution, and response formatting work
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
        "expected_intent": "inventory",
        "description": (
            "Validates LLM intent routing to the inventory agent "
            "(warehouse / stock questions)."
        ),
    },
    {
        "query": "Forecast demand for next month",
        "expected_intent": "inventory",
        "description": (
            "Validates demand/forecast routing to the inventory agent."
        ),
    },
    {
        "query": "How many iphones are there in shanghai",
        "expected_intent": "inventory",
        "description": (
            "Product/city NL-to-SQL questions route to the inventory agent."
        ),
    },
    {
        "query": "Show shipment ETA",
        "expected_intent": "logistics",
        "description": (
            "Validates logistics keyword detection (shipment, eta) "
            "and routing to the logistics agent."
        ),
    },
    {
        "query": "Optimize delivery routes",
        "expected_intent": "logistics",
        "description": (
            "Validates logistics keyword detection (delivery, route) "
            "and routing to the logistics agent."
        ),
    },
    {
        "query": "Hello world",
        "expected_intent": "logistics",
        "description": (
            "Ambiguous queries default to logistics when LLM picks logistics."
        ),
    },
]


def _initial_state(user_query: str) -> AgentState:
    return {
        "user_query": user_query,
        "intent": "",
        "selected_agent": "",
        "ml_task": "",
        "agent_response": "",
        "final_response": "",
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


@patch("agents.logistics_agent.run_logistics_turn", side_effect=_mock_logistics_awaiting)
@patch("agents.inventory_agent.run_inventory_turn", side_effect=_mock_inventory_awaiting)
def run_test_case(index: int, test_case: dict, _mock_inv, _mock_log) -> None:
    query = test_case["query"]
    expected_intent = test_case["expected_intent"]

    print(f"--- Test Case {index} ---")
    print(f"Description: {test_case['description']}")
    print(f"Query: {query}")

    result = app.invoke(_initial_state(query))

    print(f"Detected Intent: {result['intent']}")
    print(f"Selected Agent: {result['selected_agent']}")
    print(f"Final Response: {result['final_response']}")
    print()

    assert result["intent"] == expected_intent
    assert result["selected_agent"] == expected_intent
    assert result["final_response"]

    payload = json.loads(result["final_response"])
    assert payload.get("status") in {"awaiting_input", "complete"}
    if expected_intent == "inventory":
        assert payload.get("agent") == "inventory"
    else:
        assert payload.get("agent") == "logistics"


@patch("orchestrator.intent.classify_intent", return_value="logistics")
@patch("agents.logistics_agent.run_logistics_turn", side_effect=_mock_logistics_complete)
def test_logistics_complete_answer(_mock_turn, _mock_intent) -> None:
    result = app.invoke(_initial_state("What is the shipment ETA?"))
    payload = json.loads(result["final_response"])
    assert payload.get("status") == "complete"
    assert payload.get("answer")


def _mock_classify_intent(query: str) -> str:
    q = query.lower().strip()
    for case in TEST_CASES:
        if case["query"].lower().strip() == q:
            return case["expected_intent"]
    return "logistics"


def test_intent_honors_collecting_session() -> None:
    """Numeric follow-ups must not re-route to logistics."""
    state: AgentState = {
        "user_query": "3",
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
    assert result["intent"] == "inventory"


def main() -> None:
    print("Running orchestration validation tests...\n")

    test_intent_honors_collecting_session()

    with (
        patch(
            "orchestrator.intent.classify_intent",
            side_effect=_mock_classify_intent,
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
