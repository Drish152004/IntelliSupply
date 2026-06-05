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

import sys
import json
from pathlib import Path

# Add repo root to sys.path to allow importing security package
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from security.pii.masker import default_masker
from security.guardrails.prompt_guard import check_prompt_injection
from security.audit.logger import log_query, log_blocked_prompt


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
    # 1. Prompt Injection Protection
    is_safe, error_msg = check_prompt_injection(user_query)
    if not is_safe:
        log_blocked_prompt(user_query, "Prompt injection pattern matched.")
        blocked_response = json.dumps({
            "agent": "security_guard",
            "status": "complete",
            "answer": error_msg or "Security Alert: Input query rejected due to safety policy violation.",
            "session": None
        })
        return {
            "user_query": user_query,
            "intent": "blocked",
            "selected_agent": "blocked",
            "ml_task": "",
            "agent_response": blocked_response,
            "final_response": blocked_response,
        }

    # 2. PII Masking
    masked_query = default_masker.mask_text(user_query)
    log_query(user_query, masked_query)

    initial_state: AgentState = {
        "user_query": masked_query,
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
