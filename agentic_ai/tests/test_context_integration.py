"""Integration tests for Phase 5 context resolution in the orchestrator."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent
for path in (str(ROOT), str(REPO_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from context.context_node import check_query_completeness, resolve_context
from context.graph_resolver import reset_graph_resolver
from context.resolver import reset_context_resolver
from graph_retrieval.graph_node import reset_graph_retriever
from orchestrator.cache_node import reset_cache_service
from orchestrator.graph import run_orchestrator
from orchestrator.state import AgentState


def _base_state(**extra) -> AgentState:
    state: AgentState = {
        "user_query": "Predict ETA",
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
        "cache_hit": False,
        "cache_key": None,
        "cached_result": None,
        "entities": {},
        "graph_hit": False,
        "graph_result": None,
        "authorization_denied": False,
        "ready_for_ml": False,
        "payload": None,
        "resolved_context": None,
        "graph_enriched_fields": [],
        "user_supplied_fields": [],
        "missing_fields": [],
        "clarification_needed": False,
        "clarification_type": None,
        "clarification_question": None,
    }
    state.update(extra)
    return state


@pytest.fixture(autouse=True)
def _reset_services() -> None:
    reset_cache_service()
    reset_graph_retriever()
    reset_graph_resolver()
    reset_context_resolver()
    yield
    reset_cache_service()
    reset_graph_retriever()
    reset_graph_resolver()
    reset_context_resolver()


def test_query_completeness_node_hitl_entity() -> None:
    result = check_query_completeness(_base_state(user_query="Predict ETA"))
    assert result["clarification_needed"] is True
    assert result["clarification_type"] == "ENTITY"
    payload = json.loads(result["agent_response"])
    assert payload["status"] == "awaiting_input"
    assert "order" in payload["question"].lower()


def test_query_completeness_node_passes_with_order() -> None:
    result = check_query_completeness(
        _base_state(user_query="Predict ETA for order ORD123")
    )
    assert result["clarification_needed"] is False
    assert result["entities"]["order_id"] == "ORD123"


@patch("context.context_node.get_context_resolver")
def test_context_resolver_node_ready(mock_get_resolver) -> None:
    mock_resolver = MagicMock()
    mock_resolution = MagicMock()
    mock_resolution.ready_for_ml = True
    mock_resolution.payload = {
        "delivery_user_id": "C001",
        "from_dipan_id": "42",
        "aoi_id": "7",
        "receipt_time": "2026-06-05T12:00:00",
        "receipt_lat": 30.6,
        "receipt_lng": 104.0,
        "poi_lat": 30.61,
        "poi_lng": 104.01,
    }
    mock_resolution.resolved_context = mock_resolution.payload
    mock_resolution.graph_enriched_fields = ["delivery_user_id"]
    mock_resolution.user_supplied_fields = []
    mock_resolution.missing_fields = []
    mock_resolution.clarification_needed = False
    mock_resolution.clarification_type = None
    mock_resolution.clarification_question = None
    mock_resolver.resolve.return_value = mock_resolution
    mock_get_resolver.return_value = mock_resolver

    result = resolve_context(
        _base_state(
            user_query="Predict ETA for order ORD123",
            entities={"order_id": "ORD123"},
        )
    )
    assert result["ready_for_ml"] is True
    payload = json.loads(result["agent_response"])
    assert payload["status"] == "ready_for_ml"
    assert payload["payload"]["delivery_user_id"] == "C001"


@patch("orchestrator.intent.classify_domain_task")
@patch("agents.logistics_agent.run_logistics_turn")
@patch("graph_retrieval.graph_node._retriever")
def test_orchestrator_eta_entity_clarification_before_agent(
    mock_retriever,
    mock_logistics_turn,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_prediction",
        "confidence": 0.95,
    }

    result = run_orchestrator("Predict ETA", user_role="LOGISTICS")
    assert result["clarification_needed"] is True
    assert result["clarification_type"] == "ENTITY"
    mock_logistics_turn.assert_not_called()
    mock_retriever.retrieve.assert_not_called()
    payload = json.loads(result["final_response"])
    assert payload["status"] == "clarification_required"


@patch("orchestrator.intent.classify_domain_task")
@patch("agents.logistics_agent.run_logistics_turn")
@patch("graph_retrieval.graph_node._retriever")
@patch("orchestrator.ml_node.get_ml_executor")
def test_orchestrator_eta_ready_for_ml_executes_before_agent(
    mock_get_executor,
    mock_retriever,
    mock_logistics_turn,
    mock_classify,
) -> None:
    from context.graph_resolver import GraphResolver
    from context.resolver import ContextResolver

    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_prediction",
        "confidence": 0.95,
    }
    mock_retriever.retrieve.return_value = {"found": False}
    mock_executor = MagicMock()
    from ml.ml_executor import MLExecutionOutcome

    mock_executor.execute.return_value = MLExecutionOutcome(
        success=True,
        prediction_type="eta",
        model_name="lgbm_eta_model",
        result={"eta_minutes": 55.0},
        duration_ms=10.0,
    )
    mock_get_executor.return_value = mock_executor
    mock_service = MagicMock()
    mock_service.execute.return_value = [
        {
            "delivery_user_id": "C001",
            "from_dipan_id": "42",
            "aoi_id": "7",
            "receipt_lat": 30.6,
            "receipt_lng": 104.0,
            "poi_lat": 30.61,
            "poi_lng": 104.01,
            "receipt_time": "2026-06-05T12:00:00",
        }
    ]
    graph_resolver = GraphResolver(graph_service=mock_service)
    reset_graph_resolver(graph_resolver)
    reset_context_resolver(ContextResolver(graph_resolver=graph_resolver))

    result = run_orchestrator(
        "Predict ETA for order ORD123",
        user_role="LOGISTICS",
    )
    assert result["ready_for_ml"] is True
    assert result["execution_status"] == "success"
    mock_logistics_turn.assert_not_called()
    mock_executor.execute.assert_called_once()
    payload = json.loads(result["final_response"])
    assert payload["status"] == "success"
    assert payload["source"] == "ml"
    assert payload["data"]["eta_minutes"] == 55.0


@patch("orchestrator.intent.classify_domain_task")
@patch("agents.logistics_agent.run_logistics_turn")
@patch("graph_retrieval.graph_node._retriever")
def test_orchestrator_eta_payload_clarification(
    mock_retriever,
    mock_logistics_turn,
    mock_classify,
) -> None:
    from context.graph_resolver import GraphResolver
    from context.resolver import ContextResolver

    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_prediction",
        "confidence": 0.95,
    }
    mock_retriever.retrieve.return_value = {"found": False}
    mock_service = MagicMock()
    mock_service.execute.return_value = [
        {
            "delivery_user_id": "C001",
            "from_dipan_id": "42",
            "aoi_id": "7",
            "receipt_lat": 30.6,
            "receipt_lng": 104.0,
            "poi_lat": 30.61,
            "poi_lng": 104.01,
        }
    ]
    graph_resolver = GraphResolver(graph_service=mock_service)
    reset_graph_resolver(graph_resolver)
    reset_context_resolver(ContextResolver(graph_resolver=graph_resolver))

    result = run_orchestrator(
        "Predict ETA for order ORD123",
        user_role="LOGISTICS",
    )
    assert result["clarification_needed"] is True
    assert result["clarification_type"] == "PAYLOAD"
    assert "receipt_time" in result["missing_fields"]
    mock_logistics_turn.assert_not_called()
    payload = json.loads(result["final_response"])
    assert payload["status"] == "clarification_required"


@patch("orchestrator.intent.classify_domain_task")
@patch("agents.logistics_agent.run_logistics_turn")
@patch("graph_retrieval.graph_node._retriever")
def test_orchestrator_lookup_still_routes_to_agent_on_miss(
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
    mock_logistics_turn.assert_called_once()
    payload = json.loads(result["final_response"])
    assert payload["status"] == "success"
