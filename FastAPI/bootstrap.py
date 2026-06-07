"""Ensure repo root, rag/, and FastAPI/ are on sys.path for cross-package imports."""

from __future__ import annotations

import sys
from pathlib import Path

# Repo root must be on sys.path before importing the shared config package.
REPO_ROOT = Path(__file__).resolve().parents[1]
FASTAPI_ROOT = Path(__file__).resolve().parent
RAG_ROOT = REPO_ROOT / "rag"
RAG_INVENTORY_ROOT = REPO_ROOT / "rag" / "inventory"
AGENTIC_ROOT = REPO_ROOT / "agentic_ai"
BACKEND_ROOT = REPO_ROOT / "backend"

for path in (
    str(REPO_ROOT),
    str(FASTAPI_ROOT),
    str(RAG_ROOT),
    str(RAG_INVENTORY_ROOT),
    str(AGENTIC_ROOT),
):
    if path not in sys.path:
        sys.path.insert(0, path)

from config.env import load_env

load_env()
