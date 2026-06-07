"""
Prediction cache lookup and store nodes for the orchestration graph.

Runs after context resolution when ready_for_ml and before/after ML execution.
"""

from __future__ import annotations

import logging
from typing import Any

from cache.prediction_cache_config import is_prediction_cacheable, prediction_ttl_for_task
from cache.prediction_cache_key_builder import PredictionCacheKeyBuilder
from orchestrator.cache_node import get_cache_service
from orchestrator.state import AgentState

logger = logging.getLogger(__name__)


def build_prediction_cache_payload(state: AgentState) -> dict[str, Any] | None:
    """Build the normalized payload stored for a successful ML prediction."""
    if state.get("execution_status") != "success":
        return None

    result = state.get("prediction_result")
    if not isinstance(result, dict):
        return None

    return {
        "prediction_type": state.get("prediction_type"),
        "model_name": state.get("model_name"),
        "result": result,
    }


def lookup_prediction_cache(state: AgentState) -> AgentState:
    """Attempt a prediction cache lookup when context is ready for ML."""
    task = state.get("task", "")
    updated: AgentState = {
        **state,
        "prediction_cache_hit": False,
        "prediction_cache_key": None,
        "cached_prediction_result": None,
    }

    if not state.get("ready_for_ml") or not is_prediction_cacheable(task):
        return updated

    cache_key = PredictionCacheKeyBuilder.build_from_state(state)
    if cache_key is None:
        logger.info("PREDICTION CACHE MISS\ntask=%s\nkey=<unavailable>", task)
        return updated

    cached = get_cache_service().get(cache_key)
    updated["prediction_cache_key"] = cache_key

    if cached is None:
        logger.info("PREDICTION CACHE MISS\ntask=%s\nkey=%s", task, cache_key)
        return updated

    logger.info("PREDICTION CACHE HIT\ntask=%s\nkey=%s", task, cache_key)

    cached_result = cached if isinstance(cached, dict) else {}
    ml_result = cached_result.get("result") if isinstance(cached_result.get("result"), dict) else {}

    return {
        **updated,
        "prediction_cache_hit": True,
        "cached_prediction_result": cached_result,
        "prediction_type": cached_result.get("prediction_type"),
        "model_name": cached_result.get("model_name"),
        "prediction_result": ml_result,
        "execution_status": "success",
        "execution_error": None,
    }


def store_prediction_cache(state: AgentState) -> AgentState:
    """Store successful ML prediction results in the prediction cache."""
    task = state.get("task", "")
    cache_key = state.get("prediction_cache_key")

    if state.get("prediction_cache_hit") or not is_prediction_cacheable(task) or not cache_key:
        return state

    if state.get("execution_status") != "success":
        return state

    payload = build_prediction_cache_payload(state)
    if payload is None:
        return state

    ttl = prediction_ttl_for_task(task)
    if ttl is None:
        return state

    get_cache_service().set(cache_key, payload, ttl)
    logger.info("PREDICTION CACHE STORE\ntask=%s\nttl=%s", task, ttl)
    return state
