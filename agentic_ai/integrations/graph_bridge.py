"""
Bridge from LangGraph agents to Neo4j GraphRAG (rag/graphdb/graph_rag.py).
"""

from __future__ import annotations

import re
import sys
from typing import Any

from config.env import load_env
from config.paths import RAG_ROOT

_INSUFFICIENT_PHRASES = (
    "no matching data",
    "no data was found",
    "no results",
    "not found",
    "empty result",
    "could not find",
    "no records",
    "no hubs",
    "no cities",
    "does not exist",
    "unable to find",
)

_env_loaded = False

_NOTIFICATION_MARKERS = (
    "received notification from dbms",
    "neo4jwarning",
)


def _compact_graph_error(exc: Exception) -> str:
    """Short, CLI-friendly graph error without DBMS notification noise."""
    text = str(exc).replace("\r\n", "\n")
    lines = [
        line
        for line in text.splitlines()
        if not any(marker in line.lower() for marker in _NOTIFICATION_MARKERS)
    ]
    text = "\n".join(lines).strip()

    match = re.search(r"\{message:\s*([^}]+)\}", text)
    if match:
        return match.group(1).strip()

    if len(text) > 280:
        return text[:277] + "..."
    return text or type(exc).__name__


def _ensure_graph_rag() -> None:
    global _env_loaded
    rag_path = str(RAG_ROOT)
    if rag_path not in sys.path:
        sys.path.insert(0, rag_path)
    if not _env_loaded:
        load_env()
        _env_loaded = True


def _row_is_empty(row: dict[str, Any]) -> bool:
    if not row:
        return True
    return all(v is None or v == "" for v in row.values())


def is_graph_sufficient(response: dict[str, Any]) -> bool:
    """Return True when graph query + answer are usable without ML fallback."""
    result = response.get("result")
    if result is None:
        return False
    if not isinstance(result, list):
        return False
    if len(result) == 0:
        return False
    if all(_row_is_empty(row) if isinstance(row, dict) else False for row in result):
        return False

    answer = (response.get("answer") or "").strip().lower()
    if not answer:
        return False
    for phrase in _INSUFFICIENT_PHRASES:
        if phrase in answer:
            return False
    if re.search(r"\bno\s+\w+\s+(were|was)\s+found\b", answer):
        return False

    return True


def try_graph_answer(user_question: str) -> tuple[bool, dict[str, Any] | None, str | None]:
    """
    Query the logistics graph.

    Returns:
        (used_graph, response_dict, error_message)
        - used_graph True + response when sufficient
        - used_graph False + error when call failed (caller may fall back to ML)
        - used_graph False + response when call succeeded but insufficient
    """
    _ensure_graph_rag()
    try:
        from graphdb.graph_rag import ask_graph

        response = ask_graph(user_question)
    except Exception as exc:
        return False, None, _compact_graph_error(exc)

    if is_graph_sufficient(response):
        return True, response, None
    return False, response, None
