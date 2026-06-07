"""Tests for domain/task detection in the intent node."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.intent import detect_intent
from orchestrator.state import AgentState


def _base_state(**extra) -> AgentState:
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
    }
    state.update(extra)
    return state


def test_detect_intent_honors_inventory_collecting_session() -> None:
    state = _base_state(
        inventory_session={
            "messages": [],
            "collecting": {"tool": "predict_demand", "partial": {}},
        },
    )
    result = detect_intent(state)
    assert result["domain"] == "inventory"
    assert result["task"] == "inventory_nlsql"
    assert result["intent"] == "inventory"


def test_detect_intent_honors_logistics_collecting_session() -> None:
    state = _base_state(
        user_query="55",
        task="eta_prediction",
        logistics_session={
            "messages": [],
            "collecting": {"tool": "predict_eta", "partial": {}},
        },
    )
    result = detect_intent(state)
    assert result["domain"] == "logistics"
    assert result["intent"] == "logistics"
    assert result["confidence"] == 1.0


def main() -> None:
    test_detect_intent_honors_inventory_collecting_session()
    test_detect_intent_honors_logistics_collecting_session()
    print("test_intent: all passed")


if __name__ == "__main__":
    main()
