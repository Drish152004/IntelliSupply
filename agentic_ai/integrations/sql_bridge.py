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
from openai import OpenAI
from sqlalchemy import create_engine, text

CHATBOT_ROOT = REPO_ROOT / "rag" / "inventory" / "chatbot"

_engine = None
_client: OpenAI | None = None
_generate_sql = None
_env_loaded = False


def _ensure_env() -> None:
    global _env_loaded
    if _env_loaded:
        return
    load_env()
    _env_loaded = True


def _ensure_sql_generator():
    global _generate_sql
    _ensure_env()
    if _generate_sql is not None:
        return _generate_sql
    chatbot_path = str(CHATBOT_ROOT)
    if chatbot_path not in sys.path:
        sys.path.insert(0, chatbot_path)
    from sql_generator import generate_sql

    _generate_sql = generate_sql
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


def ask_inventory_sql(question: str) -> dict[str, Any]:
    """
    NL-to-SQL for inventory Postgres (products, warehouses, inventory tables).

    Mirrors rag/inventory/chatbot/chatbot.py.
    """
    generate_sql = _ensure_sql_generator()

    generated_sql = generate_sql(question)
    generated_sql = (
        generated_sql.replace("```sql", "").replace("```", "").strip()
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

    try:
        with _db_engine().connect() as conn:
            result = conn.execute(text(generated_sql))
            rows = result.fetchall()

        formatted_prompt = f"""
        User Question:
        {question}

        SQL Result:
        {rows}

        Generate a short natural language response.
        """

        response = _llm_client().chat.completions.create(
            model="meta/llama-3.1-8b-instruct",
            messages=[{"role": "user", "content": formatted_prompt}],
            temperature=0,
        )
        final_answer = response.choices[0].message.content

        return {
            "question": question,
            "sql": generated_sql,
            "result": [list(row) for row in rows],
            "answer": final_answer,
        }
    except Exception as exc:
        return {
            "question": question,
            "sql": generated_sql,
            "result": None,
            "answer": None,
            "error": str(exc),
        }
