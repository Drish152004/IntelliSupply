"""Entity extraction node: extract and normalize identifiers only."""

from __future__ import annotations

from context.entity_extractor import EntityExtractor
from context.self_scoped import apply_self_scoped_entities
from orchestrator.hitl_session import merge_entities
from orchestrator.state import AgentState


def extract_entities_node(state: AgentState) -> AgentState:
    """Extract raw entity references and merge with any entities already on state.

    Sole producer of self_scoped. For resume turns the clarification_router has
    placed persisted entities on ``state["entities"]``; for new queries it is
    empty, so the merge is a no-op. No HITL, authorization, or task validation.
    """
    user_query = state["user_query"]
    extracted = EntityExtractor.extract(user_query)
    extracted = apply_self_scoped_entities(
        entities=extracted,
        user_query=user_query,
    )
    merged = merge_entities(state.get("entities") or {}, extracted)
    return {**state, "entities": merged}
