"""
Logistics domain agent — LLM with tools (GraphRAG, ETA, route prediction).
"""

from __future__ import annotations

import json

from agents.base_agent import BaseAgent
from agents.logistics_agent_loop import run_logistics_turn
from orchestrator.state import AgentState


class LogisticsAgent(BaseAgent):
    """Handles shipment, route, delivery, and transport-related queries."""

    def execute(self, state: AgentState) -> str:
        session = state.get("logistics_session")
        result = run_logistics_turn(state["user_query"], session)
        return json.dumps(result, indent=2, default=str)
