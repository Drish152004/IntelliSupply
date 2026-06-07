"""Single source of truth for task → ML wrapper routing."""

from __future__ import annotations

import importlib
from typing import Type

from ml.wrappers.base import BaseModelWrapper

ML_TASKS: frozenset[str] = frozenset({
    "eta_prediction",
    "route_prediction",
    "demand_forecast",
})

_WRAPPER_REGISTRY: dict[str, str] = {
    "eta_prediction": "ml.wrappers.eta_wrapper.ETAWrapper",
    "route_prediction": "ml.wrappers.route_wrapper.RouteWrapper",
    "demand_forecast": "ml.wrappers.demand_wrapper.DemandWrapper",
}


class UnsupportedMLTaskError(ValueError):
    """Raised when no wrapper is registered for a task."""


class ModelRouter:
    """Route orchestrator tasks to the correct production ML wrapper."""

    @staticmethod
    def supported_tasks() -> frozenset[str]:
        return ML_TASKS

    @staticmethod
    def get_wrapper(task: str) -> BaseModelWrapper:
        wrapper_path = _WRAPPER_REGISTRY.get(task)
        if wrapper_path is None:
            raise UnsupportedMLTaskError(f"No ML wrapper registered for task: {task}")

        module_name, class_name = wrapper_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        wrapper_cls: Type[BaseModelWrapper] = getattr(module, class_name)
        return wrapper_cls()
