"""
Shared LangGraph state passed between orchestration nodes.
"""

from typing import Any, NotRequired, TypedDict


class AgentState(TypedDict):
    """State object threaded through the orchestration graph."""

    user_query: str
    original_query: NotRequired[str]
    detected_language: NotRequired[str]
    language_hint: NotRequired[str]
    domain: str
    coarse_domain: NotRequired[str]
    task: str
    confidence: float
    agent_response: str
    final_response: str

    authenticated_user: NotRequired[dict[str, Any]]
    logistics_session: NotRequired[dict[str, Any]]
    inventory_session: NotRequired[dict[str, Any]]
    user_role: NotRequired[str]

    access_denied: NotRequired[bool]
    authorization_denied: NotRequired[bool]

    cache_hit: NotRequired[bool]
    cache_key: NotRequired[str | None]
    cached_result: NotRequired[dict[str, Any] | None]

    entities: NotRequired[dict[str, str]]
    missing_fields: NotRequired[list[str]]
    clarification_needed: NotRequired[bool]
    clarification_type: NotRequired[str | None]
    clarification_question: NotRequired[str | None]

    execution_status: NotRequired[str | None]
    execution_error: NotRequired[str | None]

    ml_payload_partial: NotRequired[dict[str, Any]]
