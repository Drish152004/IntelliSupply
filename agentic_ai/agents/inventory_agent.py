"""
Inventory domain agent.

Demand forecasting is disabled in the orchestrator until the model bundle is
re-exported for the project's Python/sklearn version. Re-enable ML calls in
execute() when lade_demand_forecaster.pkl loads in-process on your runtime.
"""

from agents.base_agent import BaseAgent
from orchestrator.state import AgentState

# Set to True after demand model works in-process (e.g. Python 3.14 + matching sklearn).
DEMAND_FORECASTING_ENABLED = False


class InventoryAgent(BaseAgent):
    """Handles inventory, stock, warehouse, and demand-related queries."""

    def execute(self, state: AgentState) -> str:
        if not DEMAND_FORECASTING_ENABLED:
            return (
                "Demand forecasting is not wired in the orchestrator yet. "
                "Route and ETA queries are handled by the logistics agent. "
                "You can still call POST /demand/predict on the unified ML API, "
                "or re-enable this agent after exporting a compatible .pkl."
            )
        # Re-enable: wire demand via fastapi/services after a compatible .pkl exists
        return "Demand forecasting is enabled but not implemented in this build."
