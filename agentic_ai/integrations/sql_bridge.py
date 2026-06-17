"""
Bridge from the inventory agent to NL-to-SQL (rag/inventory/chatbot).

Uses the same flow as chatbot.py without modifying that module.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from config.env import load_env
from config.paths import REPO_ROOT
from observability.trace_events import (
    get_current_trace_id,
    llm_input_payload,
    llm_output_payload,
    summarize_sql_rows,
    trace_llm_input,
    trace_llm_output,
    trace_nlsql_request,
    trace_nlsql_response,
    trace_sql_execute,
    trace_sql_result,
)
from openai import OpenAI
from sqlalchemy import create_engine, text

CHATBOT_ROOT = REPO_ROOT / "rag" / "inventory" / "chatbot"

INVENTORY_SCHEMA_TABLES = ("planning_dataset", "product_catalog", "hubs")

_engine = None
_client: OpenAI | None = None
_generate_sql = None
_sql_system_prompt = None
_env_loaded = False


def _ensure_env() -> None:
    global _env_loaded
    if _env_loaded:
        return
    load_env()
    _env_loaded = True


def _ensure_sql_generator():
    global _generate_sql, _sql_system_prompt
    _ensure_env()
    if _generate_sql is not None:
        return _generate_sql
    chatbot_path = str(CHATBOT_ROOT)
    if chatbot_path not in sys.path:
        sys.path.insert(0, chatbot_path)
    import env_setup  # noqa: F401
    import sql_generator as sg

    _generate_sql = sg.generate_sql
    _sql_system_prompt = sg.SYSTEM_PROMPT
    return _generate_sql


def is_inventory_domain(question: str) -> bool:
    """Same domain gate as sql_generator.generate_sql (allowed_keywords)."""
    _ensure_sql_generator()
    import sql_generator as sg

    q = question.lower()
    return any(keyword in q for keyword in sg.allowed_keywords)


def _llm_client() -> OpenAI:
    global _client
    _ensure_env()
    if _client is None:
        _client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=os.getenv("NVIDIA_API_KEY"),
        )
    return _client


def _db_engine():
    global _engine
    _ensure_env()
    if _engine is None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL not found")
        _engine = create_engine(database_url)
    return _engine


def _extract_tables_from_sql(sql: str) -> list[str]:
    lowered = sql.lower()
    return [table for table in INVENTORY_SCHEMA_TABLES if table in lowered]


def ask_inventory_sql(
    question: str,
    *,
    entities: dict[str, Any] | None = None,
    routing_metadata: dict[str, Any] | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """
    NL-to-SQL for inventory Postgres (products, warehouses, inventory tables).

    Mirrors rag/inventory/chatbot/chatbot.py.
    """
    generate_sql = _ensure_sql_generator()
    resolved_trace_id = trace_id or get_current_trace_id()

    nlsql_prompt = f"SYSTEM:\n{_sql_system_prompt or ''}\n\nUSER:\n{question}"
    trace_nlsql_request(
        {
            "user_question": question,
            "entities": entities or {},
            "schema_names": ["inventory"],
            "selected_tables": list(INVENTORY_SCHEMA_TABLES),
            "routing_metadata": routing_metadata or {},
        },
        trace_id=resolved_trace_id,
        prompt=nlsql_prompt,
    )

    generated_sql = generate_sql(question)
    generated_sql = (
        generated_sql.replace("```sql", "").replace("```", "").strip()
    )

    selected_tables = _extract_tables_from_sql(generated_sql) if generated_sql else []
    trace_nlsql_response(
        {
            "generated_sql": generated_sql,
            "confidence": None,
            "reasoning": None,
            "selected_tables": selected_tables or list(INVENTORY_SCHEMA_TABLES),
        },
        trace_id=resolved_trace_id,
    )

    if generated_sql == "INVALID_DOMAIN_QUERY":
        return {
            "question": question,
            "sql": None,
            "result": None,
            "answer": (
                "That question is outside inventory scope. "
                "Ask about stock, products, warehouses, or hubs."
            ),
            "error": "invalid_domain",
        }

    if not generated_sql.strip().lower().startswith("select"):
        return {
            "question": question,
            "sql": generated_sql,
            "result": None,
            "answer": "Blocked unsafe query.",
            "error": "unsafe_query",
        }

    trace_sql_execute({"sql": generated_sql}, trace_id=resolved_trace_id)

    try:
        with _db_engine().connect() as conn:
            result = conn.execute(text(generated_sql))
            rows = result.fetchall()
            columns = list(result.keys()) if result.keys() else []

        trace_sql_result(
            summarize_sql_rows(rows, columns),
            trace_id=resolved_trace_id,
        )

        formatted_prompt = f"""
        User Question:
        {question}

        SQL Result:
        {rows}

        Generate a short natural language response.
        """

        trace_llm_input(
            llm_input_payload(context=formatted_prompt, row_count=len(rows)),
            trace_id=resolved_trace_id,
            prompt=formatted_prompt,
        )

        response = _llm_client().chat.completions.create(
            model="meta/llama-3.1-8b-instruct",
            messages=[{"role": "user", "content": formatted_prompt}],
            temperature=0,
        )
        final_answer = response.choices[0].message.content

        trace_llm_output(
            llm_output_payload(final_answer, status="success"),
            trace_id=resolved_trace_id,
        )

        return {
            "question": question,
            "sql": generated_sql,
            "result": [list(row) for row in rows],
            "answer": final_answer,
        }
    except Exception as exc:
        trace_llm_output(
            llm_output_payload(None, status="error"),
            trace_id=resolved_trace_id,
        )
        return {
            "question": question,
            "sql": generated_sql,
            "result": None,
            "answer": None,
            "error": str(exc),
        }
