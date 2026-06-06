"""
Inventory domain agent — LLM with tools (NL-to-SQL, demand forecasting).
"""

from __future__ import annotations

import json

from agents.base_agent import BaseAgent
from agents.inventory_agent_loop import run_inventory_turn
from orchestrator.state import AgentState


class InventoryAgent(BaseAgent):
    """Handles inventory, stock, warehouse, and demand-related queries."""

    def execute(self, state: AgentState) -> str:
        session = state.get("inventory_session")
        result = run_inventory_turn(state["user_query"], session)
        return json.dumps(result, indent=2, default=str)
