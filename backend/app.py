"""Thin shim — unified app lives in FastAPI/main.py."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FASTAPI_ROOT = REPO_ROOT / "FastAPI"

for path in (str(REPO_ROOT), str(FASTAPI_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from main import app  # noqa: E402, F401
