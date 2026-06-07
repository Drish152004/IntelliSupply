"""Request and response schemas for the Copilot testing API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CopilotRequest(BaseModel):
    """Natural-language copilot query with optional session context."""

    query: str = Field(..., description="Natural language question for the orchestrator.")
    authenticated_user: dict[str, Any] | None = Field(
        default=None,
        description="Temporary identity stub until backend auth is wired.",
    )
    logistics_session: dict[str, Any] | None = Field(
        default=None,
        description="Multi-turn logistics session state from a prior response.",
    )
    inventory_session: dict[str, Any] | None = Field(
        default=None,
        description="Multi-turn inventory session state from a prior response.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"query": "Predict ETA for order ORD123"},
                {
                    "query": "Show my route",
                    "authenticated_user": {"role": "courier", "courier_id": "C001"},
                },
                {
                    "query": "Show inventory in Bangalore",
                    "authenticated_user": {"role": "inventory_manager"},
                },
            ]
        }
    }
