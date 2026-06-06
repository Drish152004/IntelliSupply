"""
Response formatting node.

Standardizes the agent output into the final response returned to the user.
Future: add confidence scores, citations, and structured output formatting.
"""

from orchestrator.state import AgentState


def format_response(state: AgentState) -> AgentState:
    """Copy the agent response into the final response field."""
    return {**state, "final_response": state["agent_response"]}
