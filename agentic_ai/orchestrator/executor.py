"""
Agent execution node.

Retrieves the selected agent from the registry and runs it against the state.
"""

from registry.agent_registry import get_agent
from orchestrator.state import AgentState


def execute_agent(state: AgentState) -> AgentState:
    """Look up and execute the selected agent, storing its response in state."""
    agent = get_agent(state["selected_agent"])
    agent_response = agent.execute(state)
    return {**state, "agent_response": agent_response}
