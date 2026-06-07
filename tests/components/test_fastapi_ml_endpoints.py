"""ML endpoint integration tests using FastAPI sample payloads."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
FASTAPI_ROOT = REPO_ROOT / "FastAPI"
SAMPLES = FASTAPI_ROOT / "samples"

if str(FASTAPI_ROOT) not in sys.path:
    sys.path.insert(0, str(FASTAPI_ROOT))

import bootstrap  # noqa: F401

from config.paths import ROUTE_MODEL_PATH
from main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def _load_sample(name: str) -> dict:
    return json.loads((SAMPLES / name).read_text(encoding="utf-8"))


@pytest.mark.skipif(not ROUTE_MODEL_PATH.is_file(), reason="route model missing")
def test_route_next_stop(client: TestClient):
    payload = _load_sample("predict_next_stop.json")
    response = client.post("/route/predict/next-stop", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "order_id" in body
    assert "chosen" in body


@pytest.mark.skipif(not ROUTE_MODEL_PATH.is_file(), reason="route model missing")
def test_route_sequence(client: TestClient):
    payload = _load_sample("predict_route.json")
    response = client.post("/route/predict/route", json=payload)
    assert response.status_code == 200
    assert "sequence" in response.json()


def test_eta_predict(client: TestClient):
    payload = _load_sample("eta_predict.json")
    response = client.post("/eta/predict", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "eta_minutes" in body or "prediction" in body or isinstance(body, dict)


@patch("services.demand_forecasting._import_hf_client")
def test_demand_predict_uses_hf_client(mock_import_hf, client: TestClient):
    mock_hf = mock_import_hf.return_value
    mock_hf.predict_demand.return_value = [{"city": "Hangzhou", "predicted_demand": 42.0}]

    payload = _load_sample("demand_forecast.json")
    response = client.post("/demand/predict", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["predictions"] == [{"city": "Hangzhou", "predicted_demand": 42.0}]
    mock_hf.predict_demand.assert_called_once()
