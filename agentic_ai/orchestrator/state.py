"""
Shared LangGraph state passed between orchestration nodes.

Each node reads from and writes to this TypedDict as the query flows through
intent detection, routing, agent execution, and response formatting.
"""

from typing import TypedDict


class AgentState(TypedDict):
    """State object threaded through the orchestration graph."""

    user_query: str
    intent: str
    selected_agent: str
    agent_response: str
    final_response: str
