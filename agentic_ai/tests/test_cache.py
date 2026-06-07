"""Unit tests for the cache module."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cache.cache_key_builder import CacheKeyBuilder
from cache.cache_service import CacheService
from cache.memory_cache import MemoryCache
from cache.ttl_config import CACHEABLE_TASKS, TASK_TTL_SECONDS, is_cacheable, ttl_for_task
from orchestrator.cache_node import (
    extract_business_result,
    get_cache_service,
    lookup_cache,
    reset_cache_service,
    store_cache,
)
from orchestrator.graph import run_orchestrator
from orchestrator.state import AgentState


def _base_state(**extra) -> AgentState:
    state: AgentState = {
        "user_query": "What is the ETA for order O123?",
        "domain": "logistics",
        "task": "eta_lookup",
        "confidence": 0.95,
        "intent": "logistics",
        "selected_agent": "",
        "ml_task": "",
        "agent_response": "",
        "final_response": "",
        "user_role": "LOGISTICS",
        "access_denied": False,
        "cache_hit": False,
        "cache_key": None,
        "cached_result": None,
    }
    state.update(extra)
    return state


@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    reset_cache_service()
    yield
    reset_cache_service()


def test_cacheable_tasks_configuration() -> None:
    assert "inventory_nlsql" in CACHEABLE_TASKS
    assert "eta_lookup" in CACHEABLE_TASKS
    assert "route_prediction" not in CACHEABLE_TASKS
    assert "next_stop_prediction" not in CACHEABLE_TASKS
    assert "eta_prediction" not in CACHEABLE_TASKS


def test_ttl_configuration() -> None:
    assert ttl_for_task("inventory_nlsql") == 300
    assert ttl_for_task("shipment_lookup") == 120
    assert ttl_for_task("courier_lookup") == 300
    assert ttl_for_task("eta_lookup") == 120
    assert ttl_for_task("demand_forecast") == 3600
    assert ttl_for_task("route_prediction") is None
    assert TASK_TTL_SECONDS["eta_lookup"] == 120


def test_cache_key_same_entities_different_wording() -> None:
    entities_a = CacheKeyBuilder.extract_entities("What is the ETA for order O123?")
    entities_b = CacheKeyBuilder.extract_entities("What is the ETA of order O123?")
    key_a = CacheKeyBuilder.build("eta_lookup", entities_a)
    key_b = CacheKeyBuilder.build("eta_lookup", entities_b)
    assert key_a == key_b


def test_cache_key_requires_entities() -> None:
    assert CacheKeyBuilder.build("eta_lookup", {}) is None
    assert CacheKeyBuilder.build_from_query("eta_lookup", "Tell me something vague") is None


def test_memory_cache_ttl_expiration() -> None:
    cache = MemoryCache()
    cache.set("key", {"eta_minutes": 32}, ttl=1)
    assert cache.get("key") == {"eta_minutes": 32}
    time.sleep(1.1)
    assert cache.get("key") is None


def test_memory_cache_thread_safe_stats() -> None:
    cache = MemoryCache()
    cache.set("a", 1, ttl=60)
    cache.get("a")
    cache.get("missing")
    stats = cache.stats()
    assert stats["stores"] == 1
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["size"] == 1


def test_cache_service_delete_and_clear() -> None:
    service = CacheService()
    service.set("key", {"value": 1}, ttl=60)
    assert service.delete("key") is True
    assert service.get("key") is None
    service.set("key", {"value": 2}, ttl=60)
    service.clear()
    assert service.stats()["size"] == 0


def test_extract_business_result_prefers_business_result_key() -> None:
    payload = {
        "status": "complete",
        "answer": "ETA is 32 minutes",
        "business_result": {"eta_minutes": 32, "order_id": "O123"},
    }
    assert extract_business_result(payload) == {
        "eta_minutes": 32,
        "order_id": "O123",
    }


def test_lookup_cache_miss_then_hit() -> None:
    miss = lookup_cache(_base_state())
    assert miss["cache_hit"] is False
    assert miss["cache_key"] is not None

    service = CacheService()
    service.set(miss["cache_key"], {"eta_minutes": 32, "order_id": "O123"}, ttl=120)
    reset_cache_service(service)

    hit = lookup_cache(_base_state())
    assert hit["cache_hit"] is True
    assert hit["cached_result"] == {"eta_minutes": 32, "order_id": "O123"}
    payload = json.loads(hit["agent_response"])
    assert payload["cached"] is True
    assert payload["result"]["eta_minutes"] == 32


def test_store_cache_skips_non_cacheable_task() -> None:
    state = _base_state(
        task="route_prediction",
        cache_key="route_prediction:abc",
        agent_response=json.dumps(
            {
                "status": "complete",
                "business_result": {"route": [1, 2, 3]},
            }
        ),
    )
    result = store_cache(state)
    assert get_cache_service().stats()["stores"] == 0
    assert result == state


def test_store_cache_persists_business_result() -> None:
    lookup = lookup_cache(_base_state())
    stored_state = store_cache(
        {
            **lookup,
            "agent_response": json.dumps(
                {
                    "status": "complete",
                    "business_result": {"eta_minutes": 32, "order_id": "O123"},
                }
            ),
        }
    )
    assert stored_state["cache_key"] == lookup["cache_key"]
    cached = get_cache_service().get(lookup["cache_key"])
    assert cached == {"eta_minutes": 32, "order_id": "O123"}


def test_store_cache_skips_formatted_answer_only() -> None:
    lookup = lookup_cache(_base_state())
    store_cache(
        {
            **lookup,
            "agent_response": json.dumps(
                {
                    "status": "complete",
                    "answer": "ETA is 32 minutes",
                }
            ),
        }
    )
    assert get_cache_service().stats()["stores"] == 0


@patch("orchestrator.intent.classify_domain_task")
@patch("agents.logistics_agent.run_logistics_turn")
def test_orchestrator_cache_hit_skips_agent(
    mock_logistics_turn,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_lookup",
        "confidence": 0.95,
    }

    business_result = {"eta_minutes": 32, "order_id": "O123"}
    key = CacheKeyBuilder.build_from_query(
        "eta_lookup",
        "What is the ETA for order O123?",
    )
    service = CacheService()
    service.set(key, business_result, ttl=120)
    reset_cache_service(service)

    result = run_orchestrator(
        "What is the ETA of order O123?",
        user_role="LOGISTICS",
    )
    assert result["cache_hit"] is True
    payload = json.loads(result["final_response"])
    assert payload["status"] == "success"
    assert payload["source"] == "cache"
    assert payload["data"] == business_result
    mock_logistics_turn.assert_not_called()


@patch("orchestrator.intent.classify_domain_task")
@patch("agents.logistics_agent.run_logistics_turn")
def test_orchestrator_cache_miss_stores_then_hits(
    mock_logistics_turn,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "eta_lookup",
        "confidence": 0.95,
    }
    mock_logistics_turn.return_value = {
        "agent": "logistics",
        "status": "complete",
        "business_result": {"eta_minutes": 45, "order_id": "O123"},
    }

    first = run_orchestrator(
        "What is the ETA for order O123?",
        user_role="LOGISTICS",
    )
    assert first["cache_hit"] is False
    assert mock_logistics_turn.call_count == 1
    assert get_cache_service().stats()["stores"] == 1

    second = run_orchestrator(
        "What is the ETA of order O123?",
        user_role="LOGISTICS",
    )
    assert second["cache_hit"] is True
    assert mock_logistics_turn.call_count == 1
    payload = json.loads(second["final_response"])
    assert payload["status"] == "success"
    assert payload["source"] == "cache"
    assert payload["data"]["eta_minutes"] == 45


@patch("orchestrator.intent.classify_domain_task")
@patch("agents.logistics_agent.run_logistics_turn")
def test_orchestrator_does_not_cache_route_prediction(
    mock_logistics_turn,
    mock_classify,
) -> None:
    mock_classify.return_value = {
        "domain": "logistics",
        "task": "route_prediction",
        "confidence": 0.95,
    }
    mock_logistics_turn.return_value = {
        "agent": "logistics",
        "status": "complete",
        "business_result": {"route": [1, 2, 3]},
    }

    run_orchestrator("Predict route for order O123", user_role="LOGISTICS")
    run_orchestrator("Predict route for order O123", user_role="LOGISTICS")
    # Phase 5: ML tasks stop at context resolver — agent is never invoked.
    assert mock_logistics_turn.call_count == 0
    assert get_cache_service().stats()["stores"] == 0
