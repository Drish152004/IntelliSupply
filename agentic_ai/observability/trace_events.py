"""
Centralized structured trace event helpers for orchestration observability.

All events are written to ``agentic_ai/app.log`` as JSON alongside existing
text trace lines. Payloads are redacted before emission.
"""

from __future__ import annotations

import contextvars
import json
import logging
from datetime import datetime, timezone
from typing import Any

from logging_config import setup_trace_logging
from observability.prompt_capture import capture_prompt
from observability.redaction import (
    MAX_ANSWER_PREVIEW,
    MAX_SAMPLE_ROWS,
    redact_payload,
    truncate_text,
)
from observability.state_metrics import compute_state_metrics

setup_trace_logging()

_logger = logging.getLogger("trace")

_trace_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "obs_trace_id", default=None
)


def set_current_trace_id(trace_id: str | None) -> None:
    _trace_id_var.set(trace_id)


def get_current_trace_id() -> str | None:
    return _trace_id_var.get()


def _resolve_trace_id(trace_id: str | None) -> str:
    return trace_id or get_current_trace_id() or "unknown"


def _emit(
    *,
    trace_id: str | None,
    node_name: str | None,
    event_type: str,
    payload: Any,
) -> None:
    resolved = _resolve_trace_id(trace_id)
    entry = {
        "trace_id": resolved,
        "node": node_name,
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": redact_payload(payload),
    }
    serialized = json.dumps(entry, default=str, ensure_ascii=False)
    _logger.info("[trace=%s] %s", resolved, serialized)


def trace_node_input(
    node_name: str,
    payload: dict[str, Any],
    *,
    trace_id: str | None = None,
    state: dict[str, Any] | None = None,
) -> None:
    _emit(trace_id=trace_id, node_name=node_name, event_type="NODE_INPUT", payload=payload)
    if state is not None:
        trace_state_metrics(node_name, state, trace_id=trace_id)


def trace_node_output(
    node_name: str,
    payload: dict[str, Any],
    *,
    trace_id: str | None = None,
    state: dict[str, Any] | None = None,
) -> None:
    _emit(trace_id=trace_id, node_name=node_name, event_type="NODE_OUTPUT", payload=payload)
    if state is not None:
        trace_state_metrics(node_name, state, trace_id=trace_id, phase="output")


def trace_state_metrics(
    node_name: str,
    state: dict[str, Any],
    *,
    trace_id: str | None = None,
    phase: str = "input",
) -> None:
    metrics = compute_state_metrics(state)
    metrics["phase"] = phase
    _emit(
        trace_id=trace_id,
        node_name=node_name,
        event_type="STATE_METRICS",
        payload=metrics,
    )


def trace_nlsql_request(
    payload: dict[str, Any],
    *,
    trace_id: str | None = None,
    prompt: str | None = None,
) -> None:
    _emit(trace_id=trace_id, node_name="nlsql", event_type="NLSQL_REQUEST", payload=payload)
    if prompt:
        capture_prompt(_resolve_trace_id(trace_id), "nlsql_prompt", prompt)


def trace_nlsql_response(payload: dict[str, Any], *, trace_id: str | None = None) -> None:
    _emit(trace_id=trace_id, node_name="nlsql", event_type="NLSQL_RESPONSE", payload=payload)


def trace_sql_execute(payload: dict[str, Any], *, trace_id: str | None = None) -> None:
    _emit(trace_id=trace_id, node_name="nlsql", event_type="SQL_EXECUTE", payload=payload)


def trace_sql_result(payload: dict[str, Any], *, trace_id: str | None = None) -> None:
    _emit(trace_id=trace_id, node_name="nlsql", event_type="SQL_RESULT", payload=payload)


def trace_graph_request(payload: dict[str, Any], *, trace_id: str | None = None) -> None:
    _emit(trace_id=trace_id, node_name="graphrag", event_type="GRAPH_REQUEST", payload=payload)


def trace_graph_cypher(
    payload: dict[str, Any],
    *,
    trace_id: str | None = None,
    prompt: str | None = None,
) -> None:
    _emit(trace_id=trace_id, node_name="graphrag", event_type="GRAPH_CYPHER", payload=payload)
    if prompt:
        capture_prompt(_resolve_trace_id(trace_id), "graphrag_prompt", prompt)


def trace_graph_result(payload: dict[str, Any], *, trace_id: str | None = None) -> None:
    _emit(trace_id=trace_id, node_name="graphrag", event_type="GRAPH_RESULT", payload=payload)


def trace_llm_input(
    payload: dict[str, Any],
    *,
    trace_id: str | None = None,
    prompt: str | None = None,
    prompt_label: str = "summary_prompt",
) -> None:
    _emit(trace_id=trace_id, node_name="llm", event_type="LLM_SUMMARY_INPUT", payload=payload)
    if prompt:
        capture_prompt(_resolve_trace_id(trace_id), prompt_label, prompt)


def trace_llm_output(payload: dict[str, Any], *, trace_id: str | None = None) -> None:
    _emit(trace_id=trace_id, node_name="llm", event_type="LLM_SUMMARY_OUTPUT", payload=payload)


def trace_cache_lookup(payload: dict[str, Any], *, trace_id: str | None = None) -> None:
    _emit(
        trace_id=trace_id,
        node_name="semantic_cache_lookup",
        event_type="CACHE_LOOKUP",
        payload=payload,
    )


def trace_cache_store(payload: dict[str, Any], *, trace_id: str | None = None) -> None:
    _emit(
        trace_id=trace_id,
        node_name="semantic_cache_store",
        event_type="CACHE_STORE",
        payload=payload,
    )


def summarize_sql_rows(rows: list[Any], columns: list[str] | None = None) -> dict[str, Any]:
    """Build a SQL_RESULT payload without dumping full result sets."""
    sample_rows = [list(row) for row in rows[:MAX_SAMPLE_ROWS]]
    if columns is None and rows:
        columns = [f"col_{i}" for i in range(len(rows[0]))]
    return {
        "row_count": len(rows),
        "columns": columns or [],
        "sample_rows": sample_rows,
    }


def summarize_graph_records(records: list[dict[str, Any]] | dict[str, Any] | None) -> dict[str, Any]:
    """Build a GRAPH_RESULT payload with counts and a small sample."""
    if records is None:
        return {"record_count": 0, "node_count": 0, "relationship_count": 0, "sample": []}

    if isinstance(records, dict):
        records_list = [records]
    else:
        records_list = list(records)

    sample = records_list[:MAX_SAMPLE_ROWS]
    node_count = 0
    relationship_count = 0
    for record in records_list:
        if not isinstance(record, dict):
            continue
        if "stops" in record and isinstance(record["stops"], list):
            node_count += len(record["stops"])
        for key in record:
            if key.endswith("_id") or key in {"order_id", "courier_id", "hub_id"}:
                node_count += 1
        if any(k in record for k in ("from_hub_name", "to_hub_name", "assigned_courier_id")):
            relationship_count += 1

    return {
        "record_count": len(records_list),
        "node_count": node_count,
        "relationship_count": relationship_count,
        "sample": sample,
    }


def llm_input_payload(*, context: Any, row_count: int | None = None) -> dict[str, Any]:
    context_text = str(context)
    token_estimate = max(1, len(context_text) // 4)
    sample = truncate_text(context_text, 500)
    payload: dict[str, Any] = {
        "context_chars": len(context_text),
        "token_estimate": token_estimate,
        "sample": sample,
    }
    if row_count is not None:
        payload["row_count"] = row_count
    return payload


def llm_output_payload(answer: str | None, *, status: str = "success") -> dict[str, Any]:
    preview = truncate_text(answer or "", MAX_ANSWER_PREVIEW)
    return {"answer_preview": preview, "status": status}
