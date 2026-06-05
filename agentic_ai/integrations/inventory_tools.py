"""Tool definitions and execution for the inventory LLM agent."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from integrations import ml_bridge, parameter_collector, sql_bridge

OPENAI_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "nl_to_sql",
            "description": (
                "Answer inventory questions using natural language to SQL over "
                "Postgres (products, warehouses, inventory tables). Use for "
                "stock levels, low inventory, hub/city breakdowns, and product lookups."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Natural language inventory question",
                    }
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "predict_demand",
            "description": (
                "Forecast regional package demand using the hosted demand model. "
                "Pass any feature values the user already gave; missing fields "
                "are collected interactively."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "region_id": {"type": "string"},
                    "day_of_week": {"type": "integer"},
                    "month": {"type": "integer"},
                    "day_of_month": {"type": "integer"},
                    "day_of_year": {"type": "integer"},
                    "is_weekend": {"type": "integer"},
                    "lag_1": {"type": "number"},
                    "lag_2": {"type": "number"},
                    "lag_7": {"type": "number"},
                    "lag_14": {"type": "number"},
                    "rolling_mean_7": {"type": "number"},
                    "rolling_std_7": {"type": "number"},
                    "rolling_mean_28": {"type": "number"},
                    "ds": {"type": "string"},
                },
            },
        },
    },
]


class DemandFeatureRecord(BaseModel):
    city: str
    region_id: str
    day_of_week: int = Field(..., ge=0, le=6)
    month: int = Field(..., ge=1, le=12)
    day_of_month: int = Field(..., ge=1, le=31)
    day_of_year: int = Field(..., ge=1, le=366)
    is_weekend: int = Field(..., ge=0, le=1)
    lag_1: float = Field(..., ge=0)
    lag_2: float = Field(..., ge=0)
    lag_7: float = Field(..., ge=0)
    lag_14: float = Field(..., ge=0)
    rolling_mean_7: float = Field(..., ge=0)
    rolling_std_7: float = Field(..., ge=0)
    rolling_mean_28: float = Field(..., ge=0)
    ds: str | None = None


def merge_tool_args(tool_name: str, partial: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    merged = dict(partial)
    for key, value in (args or {}).items():
        if value is not None:
            merged[key] = value
    return merged


def prepare_tool_call(
    tool_name: str,
    args: dict[str, Any],
    partial: dict[str, Any] | None,
) -> tuple[str, str, dict[str, Any]] | None:
    if tool_name not in parameter_collector.TOOL_FIELD_PLANS:
        return None

    merged = merge_tool_args(tool_name, partial or {}, args)
    step = parameter_collector.next_collection_step(tool_name, merged)
    if step:
        return step[0], step[1], merged
    return None


def _validate_demand_payload(payload: dict[str, Any]) -> None:
    records = payload.get("records") or []
    if not records:
        raise ValueError("At least one demand record is required")
    for record in records:
        DemandFeatureRecord.model_validate(record)


def execute_tool(tool_name: str, args: dict[str, Any] | None = None) -> str:
    args = args or {}

    import sys
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    from security.validators.tool_validator import validate_tool_call
    from security.audit.logger import log_executed_tool

    try:
        validate_tool_call(tool_name, args)
    except Exception as exc:
        log_executed_tool(tool_name, args, success=False, error=str(exc))
        return json.dumps({"error": "security_validation_failed", "details": str(exc)})

    try:
        if tool_name == "nl_to_sql":
            question = args.get("question", "").strip()
            if not question:
                res = json.dumps({"error": "question is required"})
                log_executed_tool(tool_name, args, success=True)
                return res
            response = sql_bridge.ask_inventory_sql(question)
            res = json.dumps(response, default=str)
            log_executed_tool(tool_name, args, success=True)
            return res

        if tool_name == "predict_demand":
            try:
                payload = parameter_collector.finalize_partial(tool_name, args)
                _validate_demand_payload(payload)
                result = ml_bridge.run_demand_prediction(payload["records"])
                res = json.dumps({"result": result, "request": payload}, default=str)
                log_executed_tool(tool_name, args, success=True)
                return res
            except ValidationError as exc:
                res = json.dumps({"error": "validation_failed", "details": exc.errors()})
                log_executed_tool(tool_name, args, success=False, error=str(exc))
                return res
            except Exception as exc:
                res = json.dumps({"error": str(exc)})
                log_executed_tool(tool_name, args, success=False, error=str(exc))
                return res

        res = json.dumps({"error": f"Unknown tool: {tool_name}"})
        log_executed_tool(tool_name, args, success=False, error=f"Unknown tool: {tool_name}")
        return res
    except Exception as exc:
        log_executed_tool(tool_name, args, success=False, error=str(exc))
        raise exc
