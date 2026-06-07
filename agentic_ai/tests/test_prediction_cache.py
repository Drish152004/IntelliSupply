"""Unit tests for ML prediction cache key building and node behavior."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cache.prediction_cache_config import (
    PREDICTION_CACHEABLE_TASKS,
    PREDICTION_TASK_TTL_SECONDS,
    is_prediction_cacheable,
    prediction_ttl_for_task,
)
from cache.prediction_cache_key_builder import PredictionCacheKeyBuilder
from orchestrator.cache_node import get_cache_service, reset_cache_service
from orchestrator.prediction_cache_node import (
    build_prediction_cache_payload,
    lookup_prediction_cache,
    store_prediction_cache,
)
from orchestrator.state import AgentState


def _base_state(**extra) -> AgentState:
    state: AgentState = {
        "user_query": "Predict ETA for order ORD123",
        "domain": "logistics",
        "task": "eta_prediction",
        "confidence": 0.95,
        "intent": "logistics",
        "selected_agent": "",
        "ml_task": "",
        "agent_response": "",
        "final_response": "",
        "user_role": "LOGISTICS",
        "access_denied": False,
        "ready_for_ml": True,
        "entities": {"order_id": "ORD123"},
        "payload": {"order_id": "ORD123"},
        "prediction_cache_hit": False,
        "prediction_cache_key": None,
        "cached_prediction_result": None,
    }
    state.update(extra)
    return state


@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    reset_cache_service()
    yield
    reset_cache_service()


def test_prediction_cacheable_tasks_configuration() -> None:
    assert "eta_prediction" in PREDICTION_CACHEABLE_TASKS
    assert "route_prediction" in PREDICTION_CACHEABLE_TASKS
    assert "demand_forecast" in PREDICTION_CACHEABLE_TASKS
    assert prediction_ttl_for_task("eta_prediction") == 300
    assert prediction_ttl_for_task("route_prediction") == 300
    assert prediction_ttl_for_task("demand_forecast") == 3600
    assert PREDICTION_TASK_TTL_SECONDS["eta_prediction"] == 300


def test_prediction_cache_key_eta_uses_order_id() -> None:
    key = PredictionCacheKeyBuilder.build(
        "eta_prediction",
        entities={"order_id": "ORD123"},
    )
    assert key == "eta_prediction:ORD123"


def test_prediction_cache_key_route_uses_order_id() -> None:
    key = PredictionCacheKeyBuilder.build(
        "route_prediction",
        entities={"order_id": "ORD456"},
        payload={"order_id": "ORD456"},
    )
    assert key == "route_prediction:ORD456"


def test_prediction_cache_key_demand_uses_city_and_horizon() -> None:
    key = PredictionCacheKeyBuilder.build(
        "demand_forecast",
        entities={"city": "Bangalore", "horizon": "7"},
        payload={"city": "Bangalore", "horizon": "7"},
    )
    assert key == "demand_forecast:BANGALORE:7"


def test_prediction_cache_key_does_not_use_raw_query() -> None:
    state = _base_state(user_query="completely different wording")
    key = PredictionCacheKeyBuilder.build_from_state(state)
    assert key == "eta_prediction:ORD123"


def test_prediction_cache_key_requires_business_identifiers() -> None:
    assert PredictionCacheKeyBuilder.build("eta_prediction", entities={}) is None
    assert PredictionCacheKeyBuilder.build(
        "demand_forecast",
        entities={"city": "Bangalore"},
    ) is None


def test_build_prediction_cache_payload_from_ml_state() -> None:
    payload = build_prediction_cache_payload(
        _base_state(
            execution_status="success",
            prediction_type="eta",
            model_name="lgbm_eta_model",
            prediction_result={"eta_minutes": 42.0},
        )
    )
    assert payload == {
        "prediction_type": "eta",
        "model_name": "lgbm_eta_model",
        "result": {"eta_minutes": 42.0},
    }


def test_lookup_prediction_cache_miss_then_hit() -> None:
    miss = lookup_prediction_cache(_base_state())
    assert miss["prediction_cache_hit"] is False
    assert miss["prediction_cache_key"] == "eta_prediction:ORD123"

    service = get_cache_service()
    service.set(
        miss["prediction_cache_key"],
        {
            "prediction_type": "eta",
            "model_name": "lgbm_eta_model",
            "result": {"eta_minutes": 42.0},
        },
        ttl=300,
    )

    hit = lookup_prediction_cache(_base_state())
    assert hit["prediction_cache_hit"] is True
    assert hit["cached_prediction_result"]["result"]["eta_minutes"] == 42.0
    assert hit["prediction_result"]["eta_minutes"] == 42.0
    assert hit["execution_status"] == "success"


def test_lookup_prediction_cache_skips_when_not_ready_for_ml() -> None:
    result = lookup_prediction_cache(_base_state(ready_for_ml=False))
    assert result["prediction_cache_hit"] is False
    assert result["prediction_cache_key"] is None


def test_lookup_prediction_cache_skips_non_prediction_task() -> None:
    result = lookup_prediction_cache(
        _base_state(task="eta_lookup", ready_for_ml=False)
    )
    assert result["prediction_cache_hit"] is False
    assert not is_prediction_cacheable("eta_lookup")


def test_store_prediction_cache_persists_ml_outcome() -> None:
    looked_up = lookup_prediction_cache(_base_state())
    stored = store_prediction_cache(
        {
            **looked_up,
            "execution_status": "success",
            "prediction_type": "eta",
            "model_name": "lgbm_eta_model",
            "prediction_result": {"eta_minutes": 55.0},
        }
    )
    assert stored["prediction_cache_key"] == "eta_prediction:ORD123"
    cached = get_cache_service().get("eta_prediction:ORD123")
    assert cached["result"]["eta_minutes"] == 55.0


def test_store_prediction_cache_skips_on_hit() -> None:
    service = get_cache_service()
    service.set(
        "eta_prediction:ORD123",
        {"prediction_type": "eta", "model_name": "x", "result": {"eta_minutes": 1.0}},
        ttl=300,
    )
    hit = lookup_prediction_cache(_base_state())
    result = store_prediction_cache(
        {
            **hit,
            "execution_status": "success",
            "prediction_type": "eta",
            "prediction_result": {"eta_minutes": 99.0},
        }
    )
    assert result["prediction_cache_hit"] is True
    assert service.get("eta_prediction:ORD123")["result"]["eta_minutes"] == 1.0
