"""
Keyword-based intent detection.

Classifies the user query as inventory or logistics before routing.
Demand forecasting is not active in the orchestrator yet; inventory intent is
kept for routing structure and will call a stub agent until re-enabled.
"""

from orchestrator.state import AgentState

# Exclude "demand" / "forecast" from inventory routing until demand ML is re-enabled.
INVENTORY_KEYWORDS = ("stock", "inventory", "warehouse")
LOGISTICS_KEYWORDS = ("shipment", "route", "delivery", "eta", "transport", "demand", "forecast")


def detect_intent(state: AgentState) -> AgentState:
    """Detect intent from the user query and update state."""
    query = state["user_query"].lower()

    inventory_score = sum(1 for keyword in INVENTORY_KEYWORDS if keyword in query)
    logistics_score = sum(1 for keyword in LOGISTICS_KEYWORDS if keyword in query)

    if inventory_score > logistics_score:
        intent = "inventory"
    elif logistics_score > inventory_score:
        intent = "logistics"
    else:
        # Default to logistics when there is no match or a tie.
        intent = "logistics"

    return {**state, "intent": intent}
