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


def run_orchestrator(user_query: str) -> AgentState:
    """Run the full orchestration pipeline for a single user query."""
    app = build_graph()
    initial_state: AgentState = {
        "user_query": user_query,
        "intent": "",
        "selected_agent": "",
        "agent_response": "",
        "final_response": "",
    }
    return app.invoke(initial_state)
