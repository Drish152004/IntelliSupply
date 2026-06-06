"""
Main LangGraph orchestration workflow.

Wires intent detection, routing, agent execution, and response formatting
into a linear graph executed for every user query.
"""

from langgraph.graph import END, START, StateGraph

from orchestrator.executor import execute_agent
from orchestrator.intent import detect_intent
from orchestrator.response_formatter import format_response
from orchestrator.router import route_to_agent
from orchestrator.state import AgentState


def build_graph():
    """Construct and compile the orchestration graph."""
    graph = StateGraph(AgentState)

    graph.add_node("intent", detect_intent)
    graph.add_node("router", route_to_agent)
    graph.add_node("executor", execute_agent)
    graph.add_node("response_formatter", format_response)

    graph.add_edge(START, "intent")
    graph.add_edge("intent", "router")
    graph.add_edge("router", "executor")
    graph.add_edge("executor", "response_formatter")
    graph.add_edge("response_formatter", END)

    return graph.compile()


# Compiled once at import; reused for every query via run_orchestrator.
ORCHESTRATOR_APP = build_graph()


def run_orchestrator(
    user_query: str,
    ml_payload_partial: dict | None = None,
    logistics_session: dict | None = None,
    inventory_session: dict | None = None,
) -> AgentState:
    """Run the full orchestration pipeline for a single user query."""
    initial_state: AgentState = {
        "user_query": user_query,
        "intent": "",
        "selected_agent": "",
        "ml_task": "",
        "agent_response": "",
        "final_response": "",
    }
    if ml_payload_partial:
        initial_state["ml_payload_partial"] = ml_payload_partial
    if logistics_session:
        initial_state["logistics_session"] = logistics_session
    if inventory_session:
        initial_state["inventory_session"] = inventory_session
    return ORCHESTRATOR_APP.invoke(initial_state)
