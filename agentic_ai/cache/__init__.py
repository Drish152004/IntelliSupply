"""Redis-backed semantic cache for the orchestrator.

Phase 2: infrastructure only. Not yet integrated into the graph or execution flow.
Exact normalized-query matching; embeddings/vector search are a later phase.
"""

from __future__ import annotations

from cache.semantic_cache import (
    health_check,
    semantic_invalidate,
    semantic_lookup,
    semantic_store,
)

__all__ = [
    "semantic_lookup",
    "semantic_store",
    "semantic_invalidate",
    "health_check",
]
