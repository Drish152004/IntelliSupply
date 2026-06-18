"""Direct RAG execution: inventory NL-SQL or Aura GraphDB logistics retrieval."""

from __future__ import annotations

import json
import logging

from integrations.aura_bridge import execute_aura_function
from integrations.sql_bridge import ask_inventory_sql
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)


def _build_logistics_response(
    *,
    status: str,
    task: str,
    function_name: str,
    payload: dict,
    result: dict,
) -> str:
    """Serialize the structured Aura execution result into agent_response."""
    return json.dumps(
        {
            "status": status,
            "domain": "logistics",
            "task": task,
            "function_name": function_name,
            "payload": payload,
            "graph_result": result,
            "result": result,
        },
        indent=2,
        default=str,
    )


def execute_rag(state: AgentState) -> AgentState:
    """Run the appropriate RAG backend using parameter preparation output."""
    if state.get("missing_required_parameters") or state.get("clarification_needed"):
        return {
            **state,
            "execution_status": "blocked",
            "execution_error": "missing_required_parameters",
            "agent_response": json.dumps(
                {
                    "status": "blocked",
                    "error_code": "MISSING_REQUIRED_PARAMETERS",
                    "missing_fields": state.get("missing_fields") or [],
                },
                indent=2,
            ),
        }

    domain = state.get("domain", "")
    task = state.get("task", "")
    query = state["user_query"]
    trace_id = state.get("trace_id")

    routing_metadata = {
        "domain": domain,
        "task": task,
        "confidence": state.get("confidence"),
        "classification_source": state.get("classification_source"),
    }

    try:
        if domain == "inventory" or task == "inventory_nlsql":
            result = ask_inventory_sql(
                query,
                entities=state.get("entities") or {},
                routing_metadata=routing_metadata,
                trace_id=trace_id,
            )
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

        function_name = state.get("function_name")
        payload = state.get("payload") or {}
        if not function_name:
            return {
                **state,
                "execution_status": "error",
                "execution_error": "missing_function_name",
                "agent_response": json.dumps(
                    {
                        "status": "error",
                        "message": f"No Aura function selected for task {task}.",
                        "stage": "rag_execution",
                    },
                    indent=2,
                ),
            }

        result = execute_aura_function(
            function_name=function_name,
            payload=payload,
            user_query=query,
            prefetched_order_route=state.get("prefetched_order_route"),
            trace_id=trace_id,
        )
        status = "complete" if result.get("success") else "error"

        agent_response = _build_logistics_response(
            status=status,
            task=task,
            function_name=function_name,
            payload=payload,
            result=result,
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
