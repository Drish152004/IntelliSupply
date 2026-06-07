"""Base wrapper contract for production ML pipelines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseModelWrapper(ABC):
    """Execute a production ML pipeline and return a normalized prediction."""

    prediction_type: str
    model_name: str

    @abstractmethod
    def run(self, context_payload: dict[str, Any]) -> dict[str, Any]:
        """
        Adapt context payload, execute the pipeline, and return:

        {
            "prediction_type": "...",
            "model_name": "...",
            "result": {...},
        }
        """
