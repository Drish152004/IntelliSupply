"""Entity extraction node: extract and normalize identifiers only."""



from __future__ import annotations



from context.entity_extractor import EntityExtractor

from context.self_scoped import apply_self_scoped_entities

from orchestrator.hitl_session import get_active_hitl_session, is_hitl_resume, merge_entities

from orchestrator.state import AgentState





def extract_entities_node(state: AgentState) -> AgentState:

    """

    Extract entities from the user query and populate state["entities"].



    Sole producer of self_scoped and self-scoped courier binding.

    No HITL, authorization, task validation, or completeness checks.

    """

    user_query = state["user_query"]

    session = get_active_hitl_session(state) or {}
    if is_hitl_resume(state) and session.get("task") == "next_stop_lookup":
        entities = EntityExtractor.extract_next_stop_position(user_query)
    else:
        entities = EntityExtractor.extract(user_query)

    entities = apply_self_scoped_entities(

        entities=entities,

        user_query=user_query,

        user_role=state.get("user_role"),

        session=state.get("logistics_session"),

    )



    if is_hitl_resume(state):

        session = get_active_hitl_session(state) or {}

        persisted = session.get("entities") or {}

        entities = merge_entities(persisted, entities)



    return {**state, "entities": entities}


