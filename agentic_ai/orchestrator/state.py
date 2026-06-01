"""
Shared LangGraph state passed between orchestration nodes.

Each node reads from and writes to this TypedDict as the query flows through
intent detection, routing, agent execution, and response formatting.
"""

from typing import Any, NotRequired, TypedDict


class AgentState(TypedDict):
    """State object threaded through the orchestration graph."""

    user_query: str
    intent: str
    selected_agent: str
    ml_task: str
    agent_response: str
    final_response: str
    ml_payload_partial: NotRequired[dict[str, Any]]
    logistics_session: NotRequired[dict[str, Any]]
