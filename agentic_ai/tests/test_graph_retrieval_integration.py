"""Integration tests for graph retrieval in the orchestrator pipeline."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from graph_retrieval.graph_node import reset_graph_retriever, retrieve_from_graph
from graph_retrieval.graph_retriever import GraphRetriever
from orchestrator.cache_node import reset_cache_service
from orchestrator.graph import run_orchestrator
from orchestrator.state import AgentState


def _base_state(**extra) -> AgentState:
    state: AgentState = {
        "user_query": "What is the ETA for order ORD123?",
        "domain": "logistics",
        "task": "eta_lookup",
        "confidence": 0.95,
        "intent": "logistics",
        "selected_agent": "",
        "ml_task": "",
        "agent_response": "",
        "final_response": "",
        "user_role": "LOGISTICS",
        "access_denied": False,
        "cache_hit": False,
        "cache_key": None,
        "cached_result": None,
        "entities": {},
        "graph_hit": False,
        "graph_result": None,
        "authorization_denied": False,
    }
    state.update(extra)
    return state


@pytest.fixture(autouse=True)
def _reset_services() -> None:
    reset_cache_service()
    reset_graph_retriever()
    yield
    reset_cache_service()
    reset_graph_retriever()


def test_graph_node_hit_sets_response() -> None:
    mock_retriever = MagicMock(spec=GraphRetriever)
    mock_retriever.retrieve.return_value = {
        "found": True,
        "result": {"order_id": "ORD123", "eta_minutes": 28},
    }
    reset_graph_retriever(mock_retriever)

    result = retrieve_from_graph(_base_state())
    assert result["graph_hit"] is True
    assert result["graph_result"]["eta_minutes"] == 28
    payload = json.loads(result["agent_response"])
    assert payload["graph_hit"] is True
    assert payload["result"]["order_id"] == "ORD123"


def test_graph_node_miss_does_not_set_response() -> None:
    mock_retriever = MagicMock(spec=GraphRetriever)
    mock_retriever.retrieve.return_value = {"found": False}
    reset_graph_retriever(mock_retriever)

    result = retrieve_from_graph(_base_state())
    assert result["graph_hit"] is False
    assert result["agent_response"] == ""


def test_graph_node_authorization_denied() -> None:
    result = retrieve_from_graph(
        _base_state(
            task="route_lookup",
            user_query="Show route for courier C555",
            user_role="COURIER",
            logistics_session={"courier_id": "C001"},
        )
    )
    assert result["authorization_denied"] is True
    payload = json.loads(result["agent_response"])
    assert payload["status"] == "denied"


def test_graph_node_skips_inventory() -> None:
    mock_retriever = MagicMock(spec=GraphRetriever)
    reset_graph_retriever(mock_retriever)

    result = retrieve_from_graph(
        _base_state(
            domain="inventory",
            task="inventory_nlsql",
            user_query="How many iphones in Shanghai?",
            user_role="INVENTORY",
        )
    )
    assert result["graph_hit"] is False
    mock_retriever.retrieve.assert_not_called()


@patch("orchestrator.intent.classify_domain_task")
@patch("agents.logistics_agent.run_logistics_turn")
@patch("graph_retrieval.graph_node._retriever")
def test_orchestrator_graph_hit_skips_agent(
    mock_retriever,
    mock_logistics_turn,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_lookup",
        "confidence": 0.95,
    }
    mock_retriever.retrieve.return_value = {
        "found": True,
        "result": {"order_id": "ORD123", "eta_minutes": 28},
    }

    result = run_orchestrator(
        "What is the ETA for order ORD123?",
        user_role="LOGISTICS",
    )
    assert result["graph_hit"] is True
    payload = json.loads(result["final_response"])
    assert payload["status"] == "success"
    assert payload["source"] == "graph"
    assert payload["data"]["eta_minutes"] == 28
    mock_logistics_turn.assert_not_called()


@patch("orchestrator.intent.classify_domain_task")
@patch("agents.logistics_agent.run_logistics_turn")
@patch("graph_retrieval.graph_node._retriever")
def test_orchestrator_graph_miss_falls_through_to_agent(
    mock_retriever,
    mock_logistics_turn,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_lookup",
        "confidence": 0.95,
    }
    mock_retriever.retrieve.return_value = {"found": False}
    mock_logistics_turn.return_value = {
        "agent": "logistics",
        "status": "complete",
        "answer": "ETA is 45 minutes.",
    }

    result = run_orchestrator(
        "What is the ETA for order ORD123?",
        user_role="LOGISTICS",
    )
    assert result["graph_hit"] is False
    mock_logistics_turn.assert_called_once()
    payload = json.loads(result["final_response"])
    assert payload["status"] == "success"
    assert payload["source"] == "agent"
    assert payload["data"]["answer"] == "ETA is 45 minutes."


@patch("orchestrator.intent.classify_domain_task")
@patch("agents.inventory_agent.run_inventory_turn")
@patch("graph_retrieval.graph_node._retriever")
def test_orchestrator_inventory_skips_graph_retrieval(
    mock_retriever,
    mock_inventory_turn,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "inventory",
        "task": "inventory_nlsql",
        "confidence": 0.95,
    }
    mock_inventory_turn.return_value = {
        "agent": "inventory",
        "status": "complete",
        "answer": "42 units available.",
    }

    run_orchestrator("How many iphones in Shanghai?", user_role="INVENTORY")
    mock_retriever.retrieve.assert_not_called()
    mock_inventory_turn.assert_called_once()
