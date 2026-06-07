"""
Graph retrieval node for the orchestration pipeline.

Runs after cache lookup and before agent routing.
"""

from __future__ import annotations

import json
import logging
import re

from graph_retrieval.cypher_generator import CypherGenerator
from context.entity_extractor import EntityExtractor
from graph_retrieval.graph_authorizer import GraphAuthorizer
from graph_retrieval.graph_retriever import GraphRetriever
from orchestrator.rbac.role_mapper import IDENTITY_REQUIRED_MESSAGE
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)

_retriever = GraphRetriever()


def get_graph_retriever() -> GraphRetriever:
    """Return the shared graph retriever instance (for tests)."""
    return _retriever


def reset_graph_retriever(retriever: GraphRetriever | None = None) -> None:
    """Replace or reset the shared graph retriever (for tests)."""
    global _retriever
    _retriever = retriever if retriever is not None else GraphRetriever()


def _agent_name_for_domain(domain: str) -> str:
    return domain if domain in {"inventory", "logistics"} else "logistics"


def retrieve_from_graph(state: AgentState) -> AgentState:
    """Attempt graph-first retrieval for supported logistics lookup tasks."""
    task = state.get("task", "")
    domain = state.get("domain", "logistics")
    role = state.get("user_role")
    user_query = state["user_query"]
    session = state.get("logistics_session")

    updated: AgentState = {
        **state,
        "graph_hit": False,
        "graph_result": None,
        "authorization_denied": False,
    }

    if domain == "inventory" or not CypherGenerator.is_graph_answerable(task):
        return updated

    if task == "shipment_lookup" and re.search(
        r"\b(how many|count|number of)\b",
        user_query,
        re.I,
    ):
        return updated

    if not role:
        return {
            **updated,
            "authorization_denied": True,
            "agent_response": json.dumps(
                {"status": "denied", "reason": IDENTITY_REQUIRED_MESSAGE},
                indent=2,
            ),
        }

    entities = dict(state.get("entities") or {})
    if not entities:
        entities = EntityExtractor.extract(user_query)
    entities = GraphAuthorizer.resolve_courier_id(
        entities=entities,
        user_query=user_query,
        session=session,
    )
    updated["entities"] = entities

    logger.info(
        "ENTITYS EXTRACTED\ntask=%s\nentities=%s",
        task,
        entities,
    )

    allowed, reason = GraphAuthorizer.check(
        role=role,
        task=task,
        entities=entities,
        user_query=user_query,
        session=session,
    )
    if not allowed:
        return {
            **updated,
            "authorization_denied": True,
            "agent_response": json.dumps(
                {"status": "denied", "reason": reason},
                indent=2,
            ),
        }

    retrieval = _retriever.retrieve(task, entities)
    if not retrieval.get("found"):
        return updated

    graph_result = retrieval.get("result")
    agent_response = json.dumps(
        {
            "agent": _agent_name_for_domain(domain),
            "status": "complete",
            "graph_hit": True,
            "result": graph_result,
        },
        indent=2,
        default=str,
    )
    return {
        **updated,
        "graph_hit": True,
        "graph_result": graph_result,
        "agent_response": agent_response,
    }
