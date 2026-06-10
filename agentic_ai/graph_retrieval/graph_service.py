"""Aura graph execution service for graph retrieval."""

from __future__ import annotations

import logging
import sys
from typing import Any

from config.paths import RAG_ROOT

logger = logging.getLogger(__name__)

_service: "GraphService | None" = None
_aura_imported = False


def _ensure_aura_path() -> None:
    global _aura_imported
    rag_path = str(RAG_ROOT)
    if rag_path not in sys.path:
        sys.path.insert(0, rag_path)
    _aura_imported = True


class GraphService:
    """Execute read-only Cypher against the shared Aura connection."""

    def __init__(self, connection: Any | None = None) -> None:
        self._connection = connection
        self._owns_connection = connection is None

    def _get_connection(self) -> Any:
        if self._connection is not None:
            return self._connection

        _ensure_aura_path()
        from aura_graphdb.aura_connection import AuraConnection

        self._connection = AuraConnection()
        self._owns_connection = True
        return self._connection

    def execute(self, cypher: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Run Cypher and return records. Failures return an empty list."""
        try:
            conn = self._get_connection()
            records = conn.execute_query(cypher, parameters or {})
            return records if isinstance(records, list) else []
        except Exception as exc:
            logger.warning("Graph query failed: %s", exc)
            return []

    def close(self) -> None:
        if self._owns_connection and self._connection is not None:
            close = getattr(self._connection, "close", None)
            if callable(close):
                close()
        self._connection = None


def get_graph_service() -> GraphService:
    """Return the shared graph service instance."""
    global _service
    if _service is None:
        _service = GraphService()
    return _service


def reset_graph_service(service: GraphService | None = None) -> None:
    """Replace or reset the shared graph service (for tests)."""
    global _service
    if _service is not None:
        _service.close()
    _service = service if service is not None else GraphService()
