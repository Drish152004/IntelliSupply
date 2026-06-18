"""

Main LangGraph orchestration workflow.

init → clarification_router → semantic_cache_lookup → coarse_authorization
  → entity_extraction → intent → entity_resolution → authorize
  → parameter_preparation → rag_executor → response_formatter
  → semantic_cache_store → END

clarification_router resumes in-progress HITL turns:
  new query / domain answer → semantic_cache_lookup
  intent answer / parameter answer → entity_extraction (bypasses cache)
  attempts exceeded → response_formatter

semantic_cache_lookup:
  cache hit  → response_formatter (serves cached response)
  cache miss → coarse_authorization

"""

from __future__ import annotations

import time

from langgraph.graph import END, START, StateGraph

from orchestrator.authorize_node import authorize_request
from orchestrator.clarification_router_node import (
    clarification_router,
    route_after_clarification_router,
)
from orchestrator.entity_extraction_node import extract_entities_node
from orchestrator.entity_resolution_node import resolve_entities_node
from orchestrator.init_node import build_initial_state, init_state
from orchestrator.intent import detect_intent
from orchestrator.intent_task_classifier import needs_intent_clarification
from orchestrator.parameter_preparation_node import prepare_parameters
from orchestrator.rag_executor import execute_rag
from orchestrator.rbac_coarse import coarse_authorization
from orchestrator.response_formatter import format_response
from orchestrator.semantic_cache_lookup_node import (
    route_after_semantic_cache_lookup,
    semantic_cache_lookup_node,
)
from orchestrator.semantic_cache_store_node import semantic_cache_store_node
from orchestrator.state import AgentState
from orchestrator.tracing import (
    begin_trace,
    end_trace,
    generate_trace_id,
    traced_node,
    traced_route,
)


def rag_executor_node(state: AgentState) -> AgentState:
    """Run RAG and normalize execution_status for downstream routing."""
    result = execute_rag(state)
    if result.get("execution_status") == "complete":
        result = {**result, "execution_status": "success"}
    return result


def _route_after_coarse_authorization(state: AgentState) -> str:
    if state.get("clarification_failed"):
        return "response_formatter"
    if state.get("clarification_needed") or state.get("access_denied"):
        return "response_formatter"
    return "entity_extraction"


def _route_after_intent(state: AgentState) -> str:
    if state.get("clarification_needed") or needs_intent_clarification(
        state.get("task", ""),
        state.get("confidence", 1.0),
    ):
        return "response_formatter"
    return "entity_resolution"


def _route_after_authorize(state: AgentState) -> str:
    if state.get("authorization_denied") or state.get("access_denied"):
        return "response_formatter"
    return "parameter_preparation"


def _route_after_parameter_preparation(state: AgentState) -> str:
    if state.get("clarification_failed"):
        return "response_formatter"
    if state.get("clarification_needed") or state.get("missing_required_parameters"):
        return "response_formatter"
    return "rag_executor"


def build_graph():
    """Construct and compile the orchestration graph."""
    graph = StateGraph(AgentState)

    graph.add_node("init_state", traced_node("init_state", init_state))
    graph.add_node(
        "clarification_router",
        traced_node("clarification_router", clarification_router),
    )
    graph.add_node(
        "semantic_cache_lookup",
        traced_node("semantic_cache_lookup", semantic_cache_lookup_node),
    )
    graph.add_node(
        "semantic_cache_store",
        traced_node("semantic_cache_store", semantic_cache_store_node),
    )
    graph.add_node(
        "coarse_authorization",
        traced_node("coarse_authorization", coarse_authorization),
    )
    graph.add_node(
        "entity_extraction",
        traced_node("entity_extraction", extract_entities_node),
    )
    graph.add_node("intent", traced_node("intent", detect_intent))
    graph.add_node(
        "entity_resolution",
        traced_node("entity_resolution", resolve_entities_node),
    )
    graph.add_node("authorize", traced_node("authorize", authorize_request))
    graph.add_node(
        "parameter_preparation",
        traced_node("parameter_preparation", prepare_parameters),
    )
    graph.add_node("rag_executor", traced_node("rag_executor", rag_executor_node))
    graph.add_node(
        "response_formatter",
        traced_node("response_formatter", format_response),
    )

    graph.add_edge(START, "init_state")
    graph.add_edge("init_state", "clarification_router")
    graph.add_conditional_edges(
        "clarification_router",
        traced_route("clarification_router", route_after_clarification_router),
    )
    graph.add_conditional_edges(
        "semantic_cache_lookup",
        traced_route("semantic_cache_lookup", route_after_semantic_cache_lookup),
    )
    graph.add_conditional_edges(
        "coarse_authorization",
        traced_route("coarse_authorization", _route_after_coarse_authorization),
    )
    graph.add_edge("entity_extraction", "intent")
    graph.add_conditional_edges(
        "intent",
        traced_route("intent", _route_after_intent),
    )
    graph.add_edge("entity_resolution", "authorize")
    graph.add_conditional_edges(
        "authorize",
        traced_route("authorize", _route_after_authorize),
    )
    graph.add_conditional_edges(
        "parameter_preparation",
        traced_route("parameter_preparation", _route_after_parameter_preparation),
    )
    graph.add_edge("rag_executor", "response_formatter")
    graph.add_edge("response_formatter", "semantic_cache_store")
    graph.add_edge("semantic_cache_store", END)

    return graph.compile()


ORCHESTRATOR_APP = build_graph()


def run_orchestrator(
    user_query: str,
    ml_payload_partial: dict | None = None,
    logistics_session: dict | None = None,
    inventory_session: dict | None = None,
    pending_clarification_session: dict | None = None,
    user_role: str | None = None,
    authenticated_user: dict | None = None,
    language_hint: str | None = None,
) -> AgentState:
    """Run the full orchestration pipeline for a single user query."""
    trace_id = generate_trace_id()
    initial_state = build_initial_state(
        user_query,
        ml_payload_partial=ml_payload_partial,
        logistics_session=logistics_session,
        inventory_session=inventory_session,
        pending_clarification_session=pending_clarification_session,
        user_role=user_role,
        authenticated_user=authenticated_user,
        language_hint=language_hint,
    )
    initial_state["trace_id"] = trace_id

    run_start = time.perf_counter()
    begin_trace(trace_id, initial_state)
    result: AgentState = initial_state
    try:
        result = ORCHESTRATOR_APP.invoke(initial_state)
        return result
    finally:
        end_trace(trace_id, result, run_start)
