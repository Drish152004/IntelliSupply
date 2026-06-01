"""
Logistics domain agent.

Future: wraps route optimization, ETA prediction, and Graph RAG services.
Phase 2: returns a dummy response to validate orchestration wiring.
"""

from agents.base_agent import BaseAgent
from orchestrator.state import AgentState


class LogisticsAgent(BaseAgent):
    """Handles shipment, route, delivery, and transport-related queries."""

    def execute(self, state: AgentState) -> str:
        return "Logistics Agent Called"
