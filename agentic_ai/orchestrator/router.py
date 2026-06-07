"""
Domain-to-agent routing.

Maps the detected domain to the agent name used by the registry.
"""

from orchestrator.state import AgentState

DOMAIN_TO_AGENT = {
    "inventory": "inventory",
    "logistics": "logistics",
}


def route_to_agent(state: AgentState) -> AgentState:
    """Map detected domain to a registered agent name."""
    selected_agent = DOMAIN_TO_AGENT.get(state["domain"], "logistics")
    return {**state, "selected_agent": selected_agent}
