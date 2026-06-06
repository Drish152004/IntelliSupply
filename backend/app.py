"""Thin shim — unified app lives in FastAPI/main.py."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FASTAPI_ROOT = REPO_ROOT / "FastAPI"

if str(FASTAPI_ROOT) not in sys.path:
    sys.path.insert(0, str(FASTAPI_ROOT))

from main import app  # noqa: E402, F401
