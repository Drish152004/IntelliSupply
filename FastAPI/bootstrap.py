"""Ensure repo root, rag/, and FastAPI/ are on sys.path for cross-package imports."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
RAG_ROOT = REPO_ROOT / "rag"
FASTAPI_ROOT = REPO_ROOT / "FastAPI"
AGENTIC_ROOT = REPO_ROOT / "agentic_ai"
BACKEND_ROOT = REPO_ROOT / "backend"

for path in (str(FASTAPI_ROOT), str(REPO_ROOT), str(RAG_ROOT), str(AGENTIC_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

for _env_path in (
    RAG_ROOT / "graphdb" / ".env",
    RAG_ROOT / "aura_graphdb" / ".env",
    REPO_ROOT / ".env",
):
    if _env_path.is_file():
        load_dotenv(_env_path, override=False)
