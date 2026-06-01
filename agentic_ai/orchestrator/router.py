"""
Intent-to-agent routing.

Maps the detected intent to the agent name used by the registry.
"""

from orchestrator.state import AgentState

INTENT_TO_AGENT = {
    "inventory": "inventory",
    "logistics": "logistics",
}


def route_to_agent(state: AgentState) -> AgentState:
    """Map detected intent to a registered agent name."""
    selected_agent = INTENT_TO_AGENT.get(state["intent"], "logistics")
    return {**state, "selected_agent": selected_agent}
