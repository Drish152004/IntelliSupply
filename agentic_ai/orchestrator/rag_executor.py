"""Direct RAG execution: inventory NL-SQL or Aura GraphDB logistics retrieval."""

from __future__ import annotations

import json
import logging

from integrations.aura_bridge import query_logistics
from integrations.sql_bridge import ask_inventory_sql
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)


def execute_rag(state: AgentState) -> AgentState:
    """Run the appropriate RAG backend based on domain."""
    domain = state.get("domain", "")
    task = state.get("task", "")
    query = state["user_query"]
    entities = state.get("entities") or {}

    try:
        if domain == "inventory" or task == "inventory_nlsql":
            result = ask_inventory_sql(query)
            status = "complete" if not result.get("error") else "error"
            agent_response = json.dumps(
                {
                    "status": status,
                    "domain": "inventory",
                    "task": task or "inventory_nlsql",
                    "answer": result.get("answer"),
                    "result": result,
                },
                indent=2,
                default=str,
            )
            return {
                **state,
                "execution_status": status,
                "execution_error": result.get("error"),
                "agent_response": agent_response,
            }

        result = query_logistics(user_query=query, task=task, entities=entities)
        status = "complete" if result.get("success") else "error"
        agent_response = json.dumps(
            {
                "status": status,
                "domain": "logistics",
                "task": task,
                "answer": result.get("answer"),
                "result": result,
            },
            indent=2,
            default=str,
        )
        return {
            **state,
            "execution_status": status,
            "execution_error": result.get("error"),
            "agent_response": agent_response,
        }

    except Exception as exc:
        logger.exception("RAG execution failed")
        return {
            **state,
            "execution_status": "error",
            "execution_error": str(exc),
            "agent_response": json.dumps(
                {"status": "error", "message": str(exc), "stage": "rag_execution"},
                indent=2,
            ),
        }
