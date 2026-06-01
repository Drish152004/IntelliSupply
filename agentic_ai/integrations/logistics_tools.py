"""Tool definitions and execution for the logistics LLM agent."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from integrations import graph_bridge, ml_bridge, parameter_collector

REPO_ROOT = Path(__file__).resolve().parents[2]
ETA_SRC = REPO_ROOT / "ml_services" / "eta-prediction" / "src"
ROUTE_ROOT = REPO_ROOT / "ml_services" / "route_prediction"

OPENAI_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "graphrag_query",
            "description": (
                "Query the logistics knowledge graph (hubs, cities, couriers, "
                "pickup orders, routes). Use for factual network questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "Natural language question for the graph",
                    }
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "predict_eta",
            "description": (
                "Predict delivery ETA in minutes for one shipment. "
                "Pass any fields the user already gave; missing fields are collected interactively."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "delivery_user_id": {"type": "integer"},
                    "from_dipan_id": {"type": "integer"},
                    "aoi_id": {"type": "integer"},
                    "receipt_time": {"type": "string"},
                    "receipt_lat": {"type": "number"},
                    "receipt_lng": {"type": "number"},
                    "poi_lat": {"type": "number"},
                    "poi_lng": {"type": "number"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "predict_next_stop",
            "description": (
                "Predict which order stop a courier should visit next. "
                "Pass known fields only."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "current_lat": {"type": "number"},
                    "current_lng": {"type": "number"},
                    "stops_completed": {"type": "integer"},
                    "route_start_time": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "predict_route_sequence",
            "description": (
                "Predict optimal visit order across multiple stops on one route. "
                "Stops are collected interactively if not provided."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

_ML_RUNNERS = {
    "predict_eta": ml_bridge.run_eta_prediction,
    "predict_next_stop": ml_bridge.run_route_next_stop,
    "predict_route_sequence": ml_bridge.run_route_sequence,
}


def _ensure_eta_import() -> None:
    path = str(ETA_SRC)
    if path not in sys.path:
        sys.path.insert(0, path)


def _ensure_route_import() -> None:
    path = str(ROUTE_ROOT)
    if path not in sys.path:
        sys.path.insert(0, path)


def _validate_ml_payload(tool_name: str, payload: dict[str, Any]) -> None:
    if tool_name == "predict_eta":
        _ensure_eta_import()
        from eta_inference import ETARequest

        ETARequest.model_validate(payload)
        return
    _ensure_route_import()
    from api.schemas import NextStopRequest, RouteSequenceRequest

    if tool_name == "predict_next_stop":
        NextStopRequest.model_validate(payload)
    else:
        RouteSequenceRequest.model_validate(payload)


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
    """
    Merge args and return (field_path, prompt, partial) if more input is needed.

    Returns None when the payload is complete and ready to execute.
    """
    if tool_name not in parameter_collector.TOOL_FIELD_PLANS:
        return None

    merged = merge_tool_args(tool_name, partial or {}, args)
    step = parameter_collector.next_collection_step(tool_name, merged)
    if step:
        return step[0], step[1], merged
    return None


def execute_tool(tool_name: str, args: dict[str, Any] | None = None) -> str:
    """Run a tool and return a JSON string for the LLM tool message."""
    args = args or {}

    if tool_name == "graphrag_query":
        question = args.get("question", "").strip()
        if not question:
            return json.dumps({"error": "question is required"})
        used, response, error = graph_bridge.try_graph_answer(question)
        if used and response:
            return json.dumps(
                {
                    "answer": response.get("answer"),
                    "cypher": response.get("cypher"),
                    "result": response.get("result"),
                },
                default=str,
            )
        if error:
            return json.dumps({"error": error, "graph_used": False})
        return json.dumps(
            {
                "answer": (response or {}).get("answer"),
                "note": "Graph returned no usable data",
                "result": (response or {}).get("result"),
            },
            default=str,
        )

    if tool_name in _ML_RUNNERS:
        try:
            payload = parameter_collector.finalize_partial(tool_name, args)
            _validate_ml_payload(tool_name, payload)
            result = _ML_RUNNERS[tool_name](payload)
            return json.dumps({"result": result, "request": payload}, default=str)
        except ValidationError as exc:
            return json.dumps({"error": "validation_failed", "details": exc.errors()})
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    return json.dumps({"error": f"Unknown tool: {tool_name}"})
