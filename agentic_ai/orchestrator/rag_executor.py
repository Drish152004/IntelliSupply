"""Direct RAG execution: inventory NL-SQL or Aura GraphDB logistics retrieval."""

from __future__ import annotations

import json
import logging

from integrations.aura_bridge import execute_aura_function, execute_dynamic_cypher
from integrations.sql_bridge import ask_inventory_sql
from orchestrator.state import AgentState
from orchestrator.task_registry import DYNAMIC_GRAPH_QUERY

logger = logging.getLogger(__name__)

_UNAVAILABLE_MESSAGE = "That information isn't currently available."


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


def _execute_dynamic_graph_query(
    state: AgentState,
    *,
    query: str,
    task: str,
    trace_id: str | None,
) -> AgentState:
    """Execute the dynamic (read-only) Cypher path with the authorized scope.

    The authorization scope is set by the authorize node: None for ADMIN /
    LOGISTICS (unscoped logistics access) or {"courier_id": bound} for a
    COURIER, which confines generation and post-filtering to their own data.
    Results are serialized into the same logistics envelope the formatter's
    graph-success path already understands.
    """
    scope = state.get("authorization_scope")
    result = execute_dynamic_cypher(
        question=query,
        scope=scope,
        entities=state.get("entities") or {},
        trace_id=trace_id,
    )

    success = bool(result.get("success"))
    status = "complete" if success else "error"
    rows = result.get("rows") or []
    graph_payload = {
        "data": rows,
        "count": result.get("count", len(rows)),
        "cypher": result.get("cypher"),
    }

    agent_response = json.dumps(
        {
            "status": status,
            "domain": "logistics",
            "task": task,
            "function_name": "dynamic_graph_query",
            "payload": {"question": query, "scope": scope},
            "graph_result": graph_payload,
            "result": graph_payload,
        },
        indent=2,
        default=str,
    )
    raw_failure = result.get("message") or result.get("error")
    if not success and raw_failure:
        logger.warning("Dynamic graph query failed (trace=%s): %s", trace_id, raw_failure)
    return {
        **state,
        "execution_status": status,
        "execution_error": None if success else _UNAVAILABLE_MESSAGE,
        "generated_cypher": result.get("cypher"),
        "agent_response": agent_response,
    }


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
        if task == DYNAMIC_GRAPH_QUERY:
            return _execute_dynamic_graph_query(state, query=query, task=task, trace_id=trace_id)

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

    except Exception:
        logger.exception("RAG execution failed")
        return {
            **state,
            "execution_status": "error",
            "execution_error": _UNAVAILABLE_MESSAGE,
            "agent_response": json.dumps(
                {"status": "error", "message": _UNAVAILABLE_MESSAGE, "stage": "rag_execution"},
                indent=2,
            ),
        }
