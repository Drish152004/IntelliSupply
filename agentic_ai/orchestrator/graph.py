"""
Main LangGraph orchestration workflow.

Wires intent detection, RBAC, cache lookup/store, query completeness,
graph retrieval, context resolution, routing, agent execution, and response
formatting into a graph executed for every user query.
"""

from langgraph.graph import END, START, StateGraph

from context.context_node import check_query_completeness, resolve_context
from context.task_requirements import is_ml_task
from graph_retrieval.graph_node import retrieve_from_graph
from orchestrator.cache_node import lookup_cache, store_cache
from orchestrator.executor import execute_agent
from orchestrator.intent import detect_intent
from orchestrator.intent_task_classifier import CONFIDENCE_THRESHOLD
from orchestrator.rbac.session_context import (
    merge_logistics_session,
    restore_user_role,
)
from orchestrator.rbac.courier_identity import resolve_courier_identity
from orchestrator.rbac_node import enforce_rbac
from orchestrator.ml_node import execute_ml
from orchestrator.prediction_cache_node import lookup_prediction_cache, store_prediction_cache
from orchestrator.response_formatter import format_response
from orchestrator.router import route_to_agent
from orchestrator.state import AgentState


def _route_after_intent(state: AgentState) -> str:
    """Skip RBAC and agent execution when classification confidence is too low."""
    if state.get("confidence", 1.0) < CONFIDENCE_THRESHOLD:
        return "response_formatter"
    return "rbac"


def _route_after_rbac(state: AgentState) -> str:
    """Skip agent execution when RBAC denies access."""
    if state.get("access_denied"):
        return "response_formatter"
    return "cache_lookup"


def _route_after_cache_lookup(state: AgentState) -> str:
    """Skip agent execution when the cache returns a hit."""
    if state.get("cache_hit"):
        return "response_formatter"
    return "query_completeness"


def _route_after_query_completeness(state: AgentState) -> str:
    """Stop for entity clarification when query entities are incomplete."""
    if state.get("clarification_needed"):
        return "response_formatter"
    return "graph_retrieval"


def _route_after_graph_retrieval(state: AgentState) -> str:
    """Skip agent execution when graph retrieval answers or denies access."""
    if state.get("graph_hit") or state.get("authorization_denied"):
        return "response_formatter"
    if is_ml_task(state.get("task", "")):
        return "context_resolver"
    return "router"


def _route_after_context_resolver(state: AgentState) -> str:
    """Route to prediction cache when ML-ready; otherwise format clarification."""
    if not state.get("ready_for_ml"):
        return "response_formatter"
    return "prediction_cache_lookup"


def _route_after_prediction_cache_lookup(state: AgentState) -> str:
    """Skip ML execution when a cached prediction is available."""
    if state.get("prediction_cache_hit"):
        return "response_formatter"
    return "ml_executor"


def build_graph():
    """Construct and compile the orchestration graph."""
    graph = StateGraph(AgentState)

    graph.add_node("intent", detect_intent)
    graph.add_node("rbac", enforce_rbac)
    graph.add_node("cache_lookup", lookup_cache)
    graph.add_node("query_completeness", check_query_completeness)
    graph.add_node("graph_retrieval", retrieve_from_graph)
    graph.add_node("context_resolver", resolve_context)
    graph.add_node("prediction_cache_lookup", lookup_prediction_cache)
    graph.add_node("ml_executor", execute_ml)
    graph.add_node("prediction_cache_store", store_prediction_cache)
    graph.add_node("router", route_to_agent)
    graph.add_node("executor", execute_agent)
    graph.add_node("cache_store", store_cache)
    graph.add_node("response_formatter", format_response)

    graph.add_edge(START, "intent")
    graph.add_conditional_edges("intent", _route_after_intent)
    graph.add_conditional_edges("rbac", _route_after_rbac)
    graph.add_conditional_edges("cache_lookup", _route_after_cache_lookup)
    graph.add_conditional_edges("query_completeness", _route_after_query_completeness)
    graph.add_conditional_edges("graph_retrieval", _route_after_graph_retrieval)
    graph.add_conditional_edges("context_resolver", _route_after_context_resolver)
    graph.add_conditional_edges("prediction_cache_lookup", _route_after_prediction_cache_lookup)
    graph.add_edge("ml_executor", "prediction_cache_store")
    graph.add_edge("prediction_cache_store", "response_formatter")
    graph.add_edge("router", "executor")
    graph.add_edge("executor", "cache_store")
    graph.add_edge("cache_store", "response_formatter")
    graph.add_edge("response_formatter", END)

    return graph.compile()


# Compiled once at import; reused for every query via run_orchestrator.
ORCHESTRATOR_APP = build_graph()


def run_orchestrator(
    user_query: str,
    ml_payload_partial: dict | None = None,
    logistics_session: dict | None = None,
    inventory_session: dict | None = None,
    user_role: str | None = None,
    authenticated_user: dict | None = None,
) -> AgentState:
    """Run the full orchestration pipeline for a single user query."""
    resolved_logistics_session = logistics_session
    resolved_role: str | None = None

    if authenticated_user:
        identity = resolve_courier_identity(authenticated_user)
        resolved_role = identity["user_role"]
        resolved_logistics_session = merge_logistics_session(
            logistics_session,
            identity.get("logistics_session"),
        )
    else:
        resolved_role = restore_user_role(
            user_role=user_role,
            logistics_session=logistics_session,
            inventory_session=inventory_session,
        )

    initial_state: AgentState = {
        "user_query": user_query,
        "domain": "",
        "task": "",
        "confidence": 0.0,
        "intent": "",
        "selected_agent": "",
        "ml_task": "",
        "agent_response": "",
        "final_response": "",
        "user_role": resolved_role,
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
        "prediction_type": None,
        "prediction_result": None,
        "model_name": None,
        "model_execution_time_ms": None,
        "execution_status": None,
        "execution_error": None,
        "prediction_cache_hit": False,
        "prediction_cache_key": None,
        "cached_prediction_result": None,
    }
    if ml_payload_partial:
        initial_state["ml_payload_partial"] = ml_payload_partial
    if resolved_logistics_session:
        initial_state["logistics_session"] = resolved_logistics_session
    if inventory_session:
        initial_state["inventory_session"] = inventory_session
    return ORCHESTRATOR_APP.invoke(initial_state)
