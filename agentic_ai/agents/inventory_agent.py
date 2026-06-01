"""
Inventory domain agent.

Future: wraps NLP-SQL retrieval and demand forecasting services.
Phase 2: returns a dummy response to validate orchestration wiring.
"""

from agents.base_agent import BaseAgent
from orchestrator.state import AgentState


class InventoryAgent(BaseAgent):
    """Handles inventory, stock, warehouse, and demand-related queries."""

    def execute(self, state: AgentState) -> str:
        return "Inventory Agent Called"
