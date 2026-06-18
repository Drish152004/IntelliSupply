from typing import Literal, Optional

from pydantic import BaseModel, Field

ScenarioType = Literal[
    "demand_change",
    "inventory_change",
    "seasonality_change",
    "promotion_toggle",
    "epidemic_toggle",
    "lead_time_change",
    "replenishment_delay",
]


class InventoryPatch(BaseModel):
    current_stock_delta: Optional[int] = Field(
        default=None,
        description=(
            "Signed unit change to current_stock. "
            "Positive increases inventory, negative decreases it."
        ),
    )
    safety_stock_multiplier: Optional[float] = Field(
        default=None,
        description="Multiplier applied to safety_stock (e.g. 1.2 for +20%).",
    )


class DemandPatch(BaseModel):
    demand_multiplier: Optional[float] = Field(
        default=None,
        description=(
            "Demand scaling factor. "
            "1.25 = +25% demand, 0.8 = -20% demand."
        ),
    )


class EventPatch(BaseModel):
    promotion: Optional[bool] = Field(
        default=None,
        description="True to turn promotion on, False to turn it off.",
    )
    seasonality: Optional[str] = Field(
        default=None,
        description="Target season: winter, spring, summer, or autumn.",
    )
    epidemic: Optional[bool] = Field(
        default=None,
        description="True to turn epidemic on, False to turn it off.",
    )


class ReplenishmentPatch(BaseModel):
    lead_time_days_delta: Optional[int] = Field(
        default=None,
        description=(
            "Signed change to lead_time_days. "
            "Positive increases lead time, negative decreases it."
        ),
    )
    actual_delay_days_delta: Optional[int] = Field(
        default=None,
        description="Additional replenishment delay in days (non-negative).",
    )
    quantity_ordered_delta: Optional[int] = Field(
        default=None,
        description="Signed change to quantity_ordered on open replenishment.",
    )


class ScenarioPatch(BaseModel):
    planning_window_days: Optional[int] = Field(
        default=None,
        description=(
            "Scenario planning horizon in days when the user specifies a window "
            "(e.g. 'next week' -> 7)."
        ),
    )
    inventory: Optional[InventoryPatch] = None
    demand: Optional[DemandPatch] = None
    event: Optional[EventPatch] = None
    replenishment: Optional[ReplenishmentPatch] = None


class ScenarioExtraction(BaseModel):
    scenario_types: list[ScenarioType] = Field(
        description=(
            "One entry per causal change implied by the user query. "
            "Use only supported V1 scenario types."
        ),
    )
    patch: ScenarioPatch = Field(
        description="Structured causal-driver changes only. Omit unset fields.",
    )


class ClarificationPrompt(BaseModel):
    field_id: str
    question: str


class ScenarioUnderstandingResult(BaseModel):
    status: Literal["complete", "needs_clarification"]
    patch: Optional[ScenarioPatch] = None
    partial_patch: Optional[ScenarioPatch] = None
    scenario_types: list[ScenarioType] = Field(default_factory=list)
    clarification_prompts: list[ClarificationPrompt] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
