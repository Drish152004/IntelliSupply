"""Entity extraction node: extract and normalize identifiers only."""

from __future__ import annotations

from context.entity_extractor import EntityExtractor
from context.self_scoped import apply_self_scoped_entities
from orchestrator.hitl_session import merge_entities
from orchestrator.state import AgentState


def extract_entities_node(state: AgentState) -> AgentState:
    """Extract raw entity references and merge with any entities already on state.

    Entity extraction is strictly domain-isolated. The authoritative domain is
    resolved upstream: ``coarse_domain`` for new queries (set by coarse
    authorization, which has already gated ambiguous/denied turns) and
    ``domain`` for intent/parameter resumes (restored from the HITL session by
    clarification_router). Only that domain's pattern set runs, so inventory and
    logistics entities can never cross-contaminate.

    Sole producer of self_scoped. For resume turns the clarification_router has
    placed persisted entities on ``state["entities"]``; for new queries it is
    empty, so the merge is a no-op. No HITL, authorization, or task validation.
    """
    user_query = state["user_query"]
    domain = state.get("coarse_domain") or state.get("domain") or ""
    extracted = EntityExtractor.extract(user_query, domain)
    extracted = apply_self_scoped_entities(
        entities=extracted,
        user_query=user_query,
    )
    merged = merge_entities(state.get("entities") or {}, extracted)
    return {**state, "entities": merged}
