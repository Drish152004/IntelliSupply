"""Configuration for ML prediction result caching (post-context-resolver)."""

from __future__ import annotations

PREDICTION_CACHEABLE_TASKS: frozenset[str] = frozenset({
    "eta_prediction",
    "route_prediction",
    "demand_forecast",
})

PREDICTION_TASK_TTL_SECONDS: dict[str, int] = {
    "eta_prediction": 300,
    "route_prediction": 300,
    "demand_forecast": 3600,
}


def is_prediction_cacheable(task: str) -> bool:
    """Return True when the task supports post-ML prediction caching."""
    return task in PREDICTION_CACHEABLE_TASKS


def prediction_ttl_for_task(task: str) -> int | None:
    """Return TTL seconds for a prediction-cacheable task."""
    return PREDICTION_TASK_TTL_SECONDS.get(task)
