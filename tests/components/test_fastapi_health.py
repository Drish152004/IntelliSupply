"""FastAPI health endpoint smoke test."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
FASTAPI_ROOT = REPO_ROOT / "FastAPI"
if str(FASTAPI_ROOT) not in sys.path:
    sys.path.insert(0, str(FASTAPI_ROOT))

import bootstrap  # noqa: F401

from main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_ok(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "services" in body


def test_root_lists_services(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert "route" in response.json()["services"]
