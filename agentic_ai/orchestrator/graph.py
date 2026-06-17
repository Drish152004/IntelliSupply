"""
Main LangGraph orchestration workflow.

init → coarse_authorization → entity_extraction → intent → parameter_validation
  → cache lookup → authorize → RAG → response_formatter
  → [cache store on success] → END
"""

import time

from langgraph.graph import END, START, StateGraph

from orchestrator.authorize_node import authorize_request
from orchestrator.entity_extraction_node import extract_entities_node
from orchestrator.init_node import build_initial_state, init_state
from orchestrator.intent import detect_intent
from orchestrator.intent_task_classifier import needs_intent_clarification
from orchestrator.parameter_validation_node import validate_parameters
from orchestrator.rag_executor import execute_rag
from orchestrator.rbac_coarse import coarse_authorization
from orchestrator.response_formatter import format_response
from orchestrator.semantic_cache_node import (
    lookup_semantic_cache,
    should_persist_to_cache,
    store_semantic_cache,
)
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
    return "parameter_validation"


def _route_after_cache_lookup(state: AgentState) -> str:
    if state.get("cache_hit"):
        return "response_formatter"
    return "authorize"


def _route_after_parameter_validation(state: AgentState) -> str:
    if state.get("clarification_failed"):
        return "response_formatter"
    if state.get("clarification_needed") or state.get("missing_required_parameters"):
        return "response_formatter"
    return "semantic_cache_lookup"


def _route_after_authorize(state: AgentState) -> str:
    if state.get("authorization_denied"):
        return "response_formatter"
    return "rag_executor"


def _route_after_response_formatter(state: AgentState) -> str:
    if should_persist_to_cache(state):
        return "semantic_cache_store"
    return END


def build_graph():
    """Construct and compile the orchestration graph."""
    graph = StateGraph(AgentState)

    graph.add_node("init_state", traced_node("init_state", init_state))
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
        "semantic_cache_lookup",
        traced_node("semantic_cache_lookup", lookup_semantic_cache),
    )
    graph.add_node(
        "parameter_validation",
        traced_node("parameter_validation", validate_parameters),
    )
    graph.add_node("authorize", traced_node("authorize", authorize_request))
    graph.add_node("rag_executor", traced_node("rag_executor", rag_executor_node))
    graph.add_node(
        "response_formatter",
        traced_node("response_formatter", format_response),
    )
    graph.add_node(
        "semantic_cache_store",
        traced_node("semantic_cache_store", store_semantic_cache),
    )

    graph.add_edge(START, "init_state")
    graph.add_edge("init_state", "coarse_authorization")
    graph.add_conditional_edges(
        "coarse_authorization",
        traced_route("coarse_authorization", _route_after_coarse_authorization),
    )
    graph.add_edge("entity_extraction", "intent")
    graph.add_conditional_edges(
        "intent",
        traced_route("intent", _route_after_intent),
    )
    graph.add_conditional_edges(
        "parameter_validation",
        traced_route("parameter_validation", _route_after_parameter_validation),
    )
    graph.add_conditional_edges(
        "semantic_cache_lookup",
        traced_route("semantic_cache_lookup", _route_after_cache_lookup),
    )
    graph.add_conditional_edges(
        "authorize",
        traced_route("authorize", _route_after_authorize),
    )
    graph.add_edge("rag_executor", "response_formatter")
    graph.add_conditional_edges(
        "response_formatter",
        traced_route("response_formatter", _route_after_response_formatter),
    )
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
