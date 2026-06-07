"""Execute production ML pipelines for orchestrator-ready payloads."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from ml.model_router import ModelRouter, UnsupportedMLTaskError
from ml.validators import PayloadValidationError

logger = logging.getLogger(__name__)

_TASK_LABELS = {
    "eta_prediction": "ETA",
    "route_prediction": "Route",
    "demand_forecast": "Demand forecast",
}


@dataclass(frozen=True)
class MLExecutionOutcome:
    success: bool
    prediction_type: str | None
    model_name: str | None
    result: dict[str, Any] | None
    duration_ms: float
    error_message: str | None = None

    def to_state_fields(self) -> dict[str, Any]:
        return {
            "prediction_type": self.prediction_type,
            "prediction_result": self.result,
            "model_name": self.model_name,
            "model_execution_time_ms": self.duration_ms,
            "execution_status": "success" if self.success else "error",
            "execution_error": self.error_message,
        }

    def to_agent_response(self, *, task: str) -> str:
        import json

        if self.success:
            return json.dumps(
                {
                    "status": "prediction_complete",
                    "task": task,
                    "prediction_type": self.prediction_type,
                    "model_name": self.model_name,
                    "result": self.result,
                    "duration_ms": self.duration_ms,
                },
                indent=2,
                default=str,
            )

        label = _TASK_LABELS.get(task, task)
        return json.dumps(
            {
                "status": "error",
                "stage": "ml_execution",
                "message": self.error_message or f"{label} model execution failed",
                "task": task,
            },
            indent=2,
            default=str,
        )


class MLExecutor:
    """Route to the correct wrapper and return a normalized prediction result."""

    def __init__(self, *, router: type[ModelRouter] = ModelRouter) -> None:
        self._router = router

    def execute(self, task: str, payload: dict[str, Any]) -> MLExecutionOutcome:
        logger.info("MODEL EXECUTION START\ntask=%s", task)
        start = time.perf_counter()

        try:
            wrapper = self._router.get_wrapper(task)
            prediction = wrapper.run(payload)
            duration_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "MODEL EXECUTION COMPLETE\ntask=%s\nmodel=%s\nduration_ms=%.2f",
                task,
                prediction["model_name"],
                duration_ms,
            )
            return MLExecutionOutcome(
                success=True,
                prediction_type=prediction["prediction_type"],
                model_name=prediction["model_name"],
                result=prediction["result"],
                duration_ms=duration_ms,
            )
        except UnsupportedMLTaskError as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            message = str(exc)
            logger.error("MODEL EXECUTION FAILED\ntask=%s\nerror=%s", task, message)
            return MLExecutionOutcome(
                success=False,
                prediction_type=None,
                model_name=None,
                result=None,
                duration_ms=duration_ms,
                error_message=message,
            )
        except PayloadValidationError as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            label = _TASK_LABELS.get(task, task)
            message = f"{label} payload validation failed: {exc}"
            logger.error("MODEL EXECUTION FAILED\ntask=%s\nerror=%s", task, message)
            return MLExecutionOutcome(
                success=False,
                prediction_type=None,
                model_name=None,
                result=None,
                duration_ms=duration_ms,
                error_message=message,
            )
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            label = _TASK_LABELS.get(task, task)
            message = f"{label} model execution failed: {exc}"
            logger.error("MODEL EXECUTION FAILED\ntask=%s\nerror=%s", task, message)
            return MLExecutionOutcome(
                success=False,
                prediction_type=None,
                model_name=None,
                result=None,
                duration_ms=duration_ms,
                error_message=message,
            )


_default_executor: MLExecutor | None = None


def get_ml_executor() -> MLExecutor:
    global _default_executor
    if _default_executor is None:
        _default_executor = MLExecutor()
    return _default_executor


def reset_ml_executor(executor: MLExecutor | None = None) -> None:
    global _default_executor
    _default_executor = executor
