"""Shared pytest fixtures for IntelliSupply."""

from __future__ import annotations

import sys

import pytest

from config.paths import AGENTIC_ROOT, FASTAPI_ROOT, RAG_ROOT, REPO_ROOT

for path in (str(REPO_ROOT), str(FASTAPI_ROOT), str(AGENTIC_ROOT), str(RAG_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from config.env import load_env
from config.paths import ROUTE_MODEL_PATH

load_env()


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def route_model_path() -> Path:
    return ROUTE_MODEL_PATH
