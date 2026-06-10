"""Ensure repo root, rag/, and FastAPI/ are on sys.path for cross-package imports."""

from __future__ import annotations

import sys
from pathlib import Path

# Repo root must be on sys.path before importing the shared config package.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from config.paths import (  # noqa: E402
    AGENTIC_ROOT,
    FASTAPI_ROOT,
    RAG_ROOT,
    REPO_ROOT,
)

RAG_INVENTORY_ROOT = REPO_ROOT / "rag" / "inventory"

for path in (
    str(REPO_ROOT),
    str(FASTAPI_ROOT),
    str(RAG_ROOT),
    str(RAG_INVENTORY_ROOT),
    str(AGENTIC_ROOT),
):
    if path not in sys.path:
        sys.path.insert(0, path)

from config.env import load_env  # noqa: E402

load_env()
