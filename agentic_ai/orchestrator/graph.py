"""
Main LangGraph orchestration workflow.

init → domain hint → cache → intent → param resolver → authorize → RAG → cache store → format
"""

from langgraph.graph import END, START, StateGraph

from orchestrator.authorize_node import authorize_request
from orchestrator.init_node import build_initial_state, init_state
from orchestrator.intent import detect_intent
from orchestrator.intent_task_classifier import needs_intent_clarification
from orchestrator.param_resolver_node import resolve_parameters
from orchestrator.rag_executor import execute_rag
from orchestrator.rbac_coarse import apply_domain_routing_hint
from orchestrator.response_formatter import format_response
from orchestrator.semantic_cache_node import lookup_semantic_cache, store_semantic_cache
from orchestrator.state import AgentState


def _route_after_domain_hint(state: AgentState) -> str:
    if state.get("clarification_needed"):
        return "response_formatter"
    return "semantic_cache_lookup"


def _route_after_cache_lookup(state: AgentState) -> str:
    if state.get("cache_hit"):
        return "response_formatter"
    return "intent"


def _route_after_intent(state: AgentState) -> str:
    if state.get("clarification_needed") or needs_intent_clarification(
        state.get("task", ""),
        state.get("confidence", 1.0),
    ):
        return "response_formatter"
    return "param_resolver"


def _route_after_param_resolver(state: AgentState) -> str:
    if state.get("clarification_needed"):
        return "response_formatter"
    return "authorize"


def _route_after_authorize(state: AgentState) -> str:
    if state.get("authorization_denied") or state.get("access_denied"):
        return "response_formatter"
    return "rag_executor"


def build_graph():
    """Construct and compile the orchestration graph."""
    graph = StateGraph(AgentState)

    graph.add_node("init_state", init_state)
    graph.add_node("domain_routing_hint", apply_domain_routing_hint)
    graph.add_node("semantic_cache_lookup", lookup_semantic_cache)
    graph.add_node("intent", detect_intent)
    graph.add_node("param_resolver", resolve_parameters)
    graph.add_node("authorize", authorize_request)
    graph.add_node("rag_executor", execute_rag)
    graph.add_node("semantic_cache_store", store_semantic_cache)
    graph.add_node("response_formatter", format_response)

    graph.add_edge(START, "init_state")
    graph.add_edge("init_state", "domain_routing_hint")
    graph.add_conditional_edges("domain_routing_hint", _route_after_domain_hint)
    graph.add_conditional_edges("semantic_cache_lookup", _route_after_cache_lookup)
    graph.add_conditional_edges("intent", _route_after_intent)
    graph.add_conditional_edges("param_resolver", _route_after_param_resolver)
    graph.add_conditional_edges("authorize", _route_after_authorize)
    graph.add_edge("rag_executor", "semantic_cache_store")
    graph.add_edge("semantic_cache_store", "response_formatter")
    graph.add_edge("response_formatter", END)

    return graph.compile()


ORCHESTRATOR_APP = build_graph()


def run_orchestrator(
    user_query: str,
    ml_payload_partial: dict | None = None,
    logistics_session: dict | None = None,
    inventory_session: dict | None = None,
    user_role: str | None = None,
    authenticated_user: dict | None = None,
    language_hint: str | None = None,
) -> AgentState:
    """Run the full orchestration pipeline for a single user query."""
    initial_state = build_initial_state(
        user_query,
        ml_payload_partial=ml_payload_partial,
        logistics_session=logistics_session,
        inventory_session=inventory_session,
        user_role=user_role,
        authenticated_user=authenticated_user,
        language_hint=language_hint,
    )
    return ORCHESTRATOR_APP.invoke(initial_state)
