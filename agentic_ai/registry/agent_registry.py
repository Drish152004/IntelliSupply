"""
Central registry mapping agent names to agent instances.

The orchestrator executor looks up agents here by name after routing.
"""

from agents.base_agent import BaseAgent
from agents.inventory_agent import InventoryAgent
from agents.logistics_agent import LogisticsAgent

# Registered agents keyed by the name used during routing.
_AGENTS: dict[str, BaseAgent] = {
    "inventory": InventoryAgent(),
    "logistics": LogisticsAgent(),
}


def get_agent(agent_name: str) -> BaseAgent:
    """Return the agent instance for the given name."""
    if agent_name not in _AGENTS:
        raise KeyError(f"No agent registered for name: {agent_name}")
    return _AGENTS[agent_name]
