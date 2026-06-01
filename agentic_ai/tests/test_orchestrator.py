"""
Validation script for Phase 2A–2E orchestration flow.

Runs sample queries through the compiled LangGraph workflow and asserts that
intent detection, routing, agent execution, and response formatting work
correctly end-to-end.
"""

import sys
from pathlib import Path

# Allow imports from the agentic_ai project root when run as a script.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.graph import build_graph
from orchestrator.state import AgentState

# Compile the LangGraph workflow once and reuse it for all test cases.
app = build_graph()

TEST_CASES = [
    {
        "query": "Show inventory levels for warehouse A",
        "expected_intent": "inventory",
        "description": (
            "Validates inventory keyword detection (inventory, warehouse) "
            "and routing to the inventory agent."
        ),
    },
    {
        "query": "Forecast demand for next month",
        "expected_intent": "inventory",
        "description": (
            "Validates inventory keyword detection (forecast, demand) "
            "and routing to the inventory agent."
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
            "Validates the default fallback path when no keywords match; "
            "should route to the logistics agent."
        ),
    },
]


def _initial_state(user_query: str) -> AgentState:
    """Build the starting state passed into the graph."""
    return {
        "user_query": user_query,
        "intent": "",
        "selected_agent": "",
        "agent_response": "",
        "final_response": "",
    }


def run_test_case(index: int, test_case: dict) -> None:
    """Execute one query through the graph and assert expected behavior."""
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

    # Assert intent detection matches the expected domain.
    assert result["intent"] == expected_intent, (
        f"Expected intent '{expected_intent}', got '{result['intent']}'"
    )

    # Assert routing maps intent to the correct registered agent.
    assert result["selected_agent"] == expected_intent, (
        f"Expected agent '{expected_intent}', got '{result['selected_agent']}'"
    )

    # Assert the agent executed and the formatter produced a non-empty response.
    assert result["final_response"], "Expected a non-empty final_response"


def main() -> None:
    """Run all orchestration test cases and report success."""
    print("Running orchestration validation tests...\n")

    for index, test_case in enumerate(TEST_CASES, start=1):
        run_test_case(index, test_case)

    print("=====================================")
    print("ALL ORCHESTRATION TESTS PASSED")
    print("=====================================")


if __name__ == "__main__":
    main()
