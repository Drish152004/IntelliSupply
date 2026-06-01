"""Tests for LLM intent classification."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.intent import (
    _parse_intent_label,
    classify_intent,
    detect_intent,
)


def test_parse_intent_label() -> None:
    assert _parse_intent_label("inventory") == "inventory"
    assert _parse_intent_label("Logistics.") == "logistics"
    assert _parse_intent_label("The answer is: inventory") == "inventory"
    assert _parse_intent_label("unknown") is None


@patch("orchestrator.intent.get_client")
def test_classify_intent_uses_llm(mock_get_client: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "inventory"
    mock_get_client.return_value.chat.completions.create.return_value = mock_response

    assert classify_intent("How many iphones are there in shanghai") == "inventory"
    call_kwargs = mock_get_client.return_value.chat.completions.create.call_args.kwargs
    messages = call_kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[-1]["content"] == "How many iphones are there in shanghai"
    assert call_kwargs["temperature"] == 0.0


@patch("orchestrator.intent.get_client")
def test_classify_intent_fallback_on_llm_error(mock_get_client: MagicMock) -> None:
    mock_get_client.return_value.chat.completions.create.side_effect = RuntimeError(
        "api down"
    )
    assert classify_intent("Forecast demand for Hangzhou") == "inventory"
    assert classify_intent("Show shipment ETA") == "logistics"


def test_detect_intent_honors_collecting_session() -> None:
    state = {
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
    assert detect_intent(state)["intent"] == "inventory"


def main() -> None:
    test_parse_intent_label()
    print("test_intent: all passed")


if __name__ == "__main__":
    main()
