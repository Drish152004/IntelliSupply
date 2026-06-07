"""
Shared LangGraph state passed between orchestration nodes.

Each node reads from and writes to this TypedDict as the query flows through
intent detection, routing, agent execution, and response formatting.
"""

from typing import Any, NotRequired, TypedDict


class AgentState(TypedDict):
    """State object threaded through the orchestration graph."""

    user_query: str
    domain: str
    task: str
    confidence: float
    intent: str
    selected_agent: str
    ml_task: str
    agent_response: str
    final_response: str
    ml_payload_partial: NotRequired[dict[str, Any]]
    logistics_session: NotRequired[dict[str, Any]]
    inventory_session: NotRequired[dict[str, Any]]
    user_role: NotRequired[str]
    access_denied: NotRequired[bool]
    cache_hit: NotRequired[bool]
    cache_key: NotRequired[str | None]
    cached_result: NotRequired[dict[str, Any] | None]
    entities: NotRequired[dict[str, str]]
    graph_hit: NotRequired[bool]
    graph_result: NotRequired[dict[str, Any] | None]
    authorization_denied: NotRequired[bool]
    resolved_context: NotRequired[dict[str, Any] | None]
    payload: NotRequired[dict[str, Any] | None]
    ready_for_ml: NotRequired[bool]
    graph_enriched_fields: NotRequired[list[str]]
    user_supplied_fields: NotRequired[list[str]]
    missing_fields: NotRequired[list[str]]
    clarification_needed: NotRequired[bool]
    clarification_type: NotRequired[str | None]
    clarification_question: NotRequired[str | None]
    prediction_type: NotRequired[str | None]
    prediction_result: NotRequired[dict[str, Any] | None]
    model_name: NotRequired[str | None]
    model_execution_time_ms: NotRequired[float | None]
    execution_status: NotRequired[str | None]
    execution_error: NotRequired[str | None]
    prediction_cache_hit: NotRequired[bool]
    prediction_cache_key: NotRequired[str | None]
    cached_prediction_result: NotRequired[dict[str, Any] | None]
