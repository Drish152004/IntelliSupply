"""Required entity fields per retrieval task (RAG-only)."""

from __future__ import annotations

from orchestrator.task_registry import QUERY_ENTITY_REQUIREMENTS


def is_ml_task(task: str) -> bool:
    """Legacy alias — ML tasks removed; always False."""
    return False


def query_entity_requirements(task: str) -> tuple[tuple[str, ...], ...] | None:
    return QUERY_ENTITY_REQUIREMENTS.get(task)
