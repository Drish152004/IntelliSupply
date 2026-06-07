"""
Agent execution node.

Retrieves the selected agent from the registry and runs it against the state.
"""

from __future__ import annotations

import json

from graph_retrieval.graph_authorizer import COURIER_SCOPED_TASKS
from orchestrator.resource_rbac import authorize_courier_resource
from registry.agent_registry import get_agent
from orchestrator.state import AgentState


def execute_agent(state: AgentState) -> AgentState:
    """Look up and execute the selected agent, storing its response in state."""
    task = state.get("task", "")
    if task in COURIER_SCOPED_TASKS:
        allowed, reason, entities = authorize_courier_resource(state)
        if not allowed:
            return {
                **state,
                "entities": entities,
                "authorization_denied": True,
                "agent_response": json.dumps(
                    {"status": "denied", "reason": reason},
                    indent=2,
                ),
            }

    agent = get_agent(state["selected_agent"])
    agent_response = agent.execute(state)
    return {**state, "agent_response": agent_response}
