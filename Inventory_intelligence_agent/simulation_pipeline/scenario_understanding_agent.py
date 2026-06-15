# scenario_understanding_agent.py

import json
import os
import re
from typing import Optional

from groq import Groq

from scenario_models import (
    ScenarioExtraction,
    ScenarioPatch,
    ScenarioUnderstandingResult,
    ScenarioType,
)
from state_models import SimulationState

VALID_SEASONS = frozenset({"winter", "spring", "summer", "autumn"})
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"

_client: Optional[Groq] = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(
            api_key=os.environ.get("GROQ_API_KEY"),
        )
    return _client


def _get_groq_model() -> str:
    return os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)

SYSTEM_PROMPT = """
You are an inventory scenario understanding agent for IntelliSupply.

Convert the user's natural-language what-if question into structured causal-driver
parameters that can be applied on top of an existing SimulationState (built from
inventory health, demand analysis, forecasts, replenishment orders, and risk data).

Rules:
- Only populate fields that represent causal drivers the user explicitly or clearly implies.
- Do not predict outcomes, modify risk metrics, or modify forecast KPIs directly.
- Do not invent magnitudes. If the user does not specify an amount, leave the magnitude
  field null so the system can ask for clarification.
- Use demand_multiplier for demand increase/decrease (1.25 = +25%, 0.8 = -20%).
- Use current_stock_delta for inventory increase/decrease (signed units).
- Use event.promotion / event.epidemic as booleans for on/off toggles.
- Use event.seasonality for season changes (winter, spring, summer, autumn).
- Use replenishment.lead_time_days_delta for lead-time increase/decrease (signed days).
- Use replenishment.actual_delay_days_delta for replenishment delay (non-negative days).
- Use planning_window_days when the user specifies a time window (e.g. "next week" -> 7).
- When the user combines multiple changes in one question, populate all relevant patch
  sections and list every detected type in scenario_types.

Supported V1 scenario types (list each one detected in scenario_types):
- demand_change
- inventory_change
- seasonality_change
- promotion_toggle
- epidemic_toggle
- lead_time_change
- replenishment_delay

Examples:

User: "What if demand increases by 25% next week?"
scenario_types: ["demand_change"]
patch: { "planning_window_days": 7, "demand": { "demand_multiplier": 1.25 } }

User: "What if demand increases?"
scenario_types: ["demand_change"]
patch: { "demand": {} }

User: "Reduce inventory by 200 units"
scenario_types: ["inventory_change"]
patch: { "inventory": { "current_stock_delta": -200 } }

User: "Switch to summer seasonality"
scenario_types: ["seasonality_change"]
patch: { "event": { "seasonality": "summer" } }

User: "Turn promotion on"
scenario_types: ["promotion_toggle"]
patch: { "event": { "promotion": true } }

User: "Turn epidemic off"
scenario_types: ["epidemic_toggle"]
patch: { "event": { "epidemic": false } }

User: "Lead time increases by 3 days"
scenario_types: ["lead_time_change"]
patch: { "replenishment": { "lead_time_days_delta": 3 } }

User: "Replenishment is delayed by 5 days"
scenario_types: ["replenishment_delay"]
patch: { "replenishment": { "actual_delay_days_delta": 5 } }

User: "What if demand increases by 20% and inventory decreases by 200 units?"
scenario_types: ["demand_change", "inventory_change"]
patch: {
  "demand": { "demand_multiplier": 1.20 },
  "inventory": { "current_stock_delta": -200 }
}
"""


def _format_state_context(state: SimulationState) -> str:
    lines = [
        f"hub_id={state.hub_id}, product_id={state.product_id}, "
        f"category={state.category}, simulation_date={state.simulation_date}",
        f"current_stock={state.inventory.current_stock}",
        f"promotion={'on' if state.event.promotion else 'off'}",
        f"seasonality={state.event.seasonality}",
        f"epidemic={'on' if state.event.epidemic else 'off'}",
        f"rolling_7_avg_demand={state.demand.rolling_7_avg_demand}",
    ]
    if state.replenishment.has_incoming_replenishment:
        lines.append(
            f"lead_time_days={state.replenishment.lead_time_days}, "
            f"actual_delay_days={state.replenishment.actual_delay_days}, "
            f"expected_arrival_date={state.replenishment.expected_arrival_date}"
        )
    else:
        lines.append("has_incoming_replenishment=false")
    return "\n".join(lines)


def _extract_with_llm(
    scenario_text: str,
    state: Optional[SimulationState] = None,
) -> ScenarioExtraction:
    user_content = scenario_text
    if state is not None:
        user_content = (
            f"Base state context:\n{_format_state_context(state)}\n\n"
            f"User scenario:\n{scenario_text}"
        )

    schema_prompt = (
        "Respond with a single JSON object matching this schema:\n"
        f"{json.dumps(ScenarioExtraction.model_json_schema(), indent=2)}"
    )

    response = _get_client().chat.completions.create(
        model=_get_groq_model(),
        messages=[
            {
                "role": "system",
                "content": f"{SYSTEM_PROMPT}\n\n{schema_prompt}",
            },
            {"role": "user", "content": user_content},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    content = response.choices[0].message.content
    if not content:
        raise ValueError("Groq returned an empty response.")

    return ScenarioExtraction.model_validate(json.loads(content))


class ClarificationChecker:
    _DEMAND_PATTERN = re.compile(
        r"\bdemand\b.*\b(increas|decreas|up|down|spike|drop|surge|fall)\w*"
        r"|\b(increas|decreas|up|down|spike|drop|surge|fall)\w*.*\bdemand\b",
        re.IGNORECASE,
    )
    _INVENTORY_PATTERN = re.compile(
        r"\b(inventory|stock|on[- ]hand)\b.*\b(increas|decreas|add|reduce|cut|raise)\w*"
        r"|\b(increas|decreas|add|reduce|cut|raise)\w*.*\b(inventory|stock|on[- ]hand)\b",
        re.IGNORECASE,
    )
    _SEASONALITY_PATTERN = re.compile(
        r"\b(seasonality|seasonal|season)\b",
        re.IGNORECASE,
    )
    _PROMOTION_PATTERN = re.compile(r"\bpromotion\b", re.IGNORECASE)
    _EPIDEMIC_PATTERN = re.compile(r"\bepidemic\b", re.IGNORECASE)
    _LEAD_TIME_PATTERN = re.compile(
        r"\blead[- ]?time\b.*\b(increas|decreas|longer|shorter|up|down)\w*"
        r"|\b(increas|decreas|longer|shorter|up|down)\w*.*\blead[- ]?time\b",
        re.IGNORECASE,
    )
    _REPLENISHMENT_DELAY_PATTERN = re.compile(
        r"\b(replenishment|shipment|delivery|order|arrival)\b.*\b(delay|late|postpone)\w*"
        r"|\b(delay|late|postpone)\w*.*\b(replenishment|shipment|delivery|order|arrival)\b",
        re.IGNORECASE,
    )

    @classmethod
    def _infer_scenario_types(
        cls,
        extraction: ScenarioExtraction,
        scenario_text: str,
    ) -> set[ScenarioType]:
        types = set(extraction.scenario_types)
        if cls._DEMAND_PATTERN.search(scenario_text):
            types.add("demand_change")
        if cls._INVENTORY_PATTERN.search(scenario_text):
            types.add("inventory_change")
        if cls._SEASONALITY_PATTERN.search(scenario_text):
            types.add("seasonality_change")
        if cls._PROMOTION_PATTERN.search(scenario_text):
            types.add("promotion_toggle")
        if cls._EPIDEMIC_PATTERN.search(scenario_text):
            types.add("epidemic_toggle")
        if cls._LEAD_TIME_PATTERN.search(scenario_text):
            types.add("lead_time_change")
        if cls._REPLENISHMENT_DELAY_PATTERN.search(scenario_text):
            types.add("replenishment_delay")
        return types

    @classmethod
    def check(
        cls,
        extraction: ScenarioExtraction,
        scenario_text: str,
        state: Optional[SimulationState] = None,
    ) -> list[str]:
        patch = extraction.patch
        scenario_types = cls._infer_scenario_types(
            extraction,
            scenario_text,
        )
        questions: list[str] = []

        if "demand_change" in scenario_types and not cls._has_demand_magnitude(patch):
            questions.append(
                "By how much should demand change? "
                "Specify a percentage (e.g. 25%) or multiplier (e.g. 1.25 for +25%)."
            )

        if "inventory_change" in scenario_types and not cls._has_inventory_magnitude(patch):
            questions.append(
                "By how many units should inventory change? "
                "Use a signed value (e.g. +500 to add stock, -200 to reduce)."
            )

        if "seasonality_change" in scenario_types and not cls._has_seasonality(patch):
            questions.append(
                "Which season should apply? "
                "Choose one: winter, spring, summer, or autumn."
            )

        if "promotion_toggle" in scenario_types and not cls._has_promotion_toggle(patch):
            questions.append(
                "Should promotion be turned on or off?"
            )

        if "epidemic_toggle" in scenario_types and not cls._has_epidemic_toggle(patch):
            questions.append(
                "Should the epidemic flag be turned on or off?"
            )

        if "lead_time_change" in scenario_types and not cls._has_lead_time_delta(patch):
            questions.append(
                "By how many days should lead time change? "
                "Use a signed value (e.g. +3 to increase, -2 to decrease)."
            )

        if (
            "replenishment_delay" in scenario_types
            and not cls._has_replenishment_delay(patch)
        ):
            questions.append(
                "By how many days should replenishment be delayed?"
            )

        if (
            state is not None
            and "replenishment_delay" in scenario_types
            and not state.replenishment.has_incoming_replenishment
        ):
            questions.append(
                "There is no incoming replenishment order in the base state. "
                "Should the scenario assume a new open order, or did you mean "
                "lead-time change instead?"
            )

        if (
            state is not None
            and "lead_time_change" in scenario_types
            and not state.replenishment.has_incoming_replenishment
        ):
            questions.append(
                "There is no incoming replenishment order in the base state, "
                "so lead time cannot be adjusted. Did you mean replenishment delay "
                "or a different scenario?"
            )

        if patch.planning_window_days is None:
            questions.append(
                "Over how many days should we simulate? "
                "For example: 7 for one week, 14 for two weeks, or 30 for one month."
            )

        return questions

    @staticmethod
    def _has_demand_magnitude(patch: ScenarioPatch) -> bool:
        return (
            patch.demand is not None
            and patch.demand.demand_multiplier is not None
        )

    @staticmethod
    def _has_inventory_magnitude(patch: ScenarioPatch) -> bool:
        if patch.inventory is None:
            return False
        return patch.inventory.current_stock_delta is not None

    @staticmethod
    def _has_seasonality(patch: ScenarioPatch) -> bool:
        return (
            patch.event is not None
            and patch.event.seasonality is not None
        )

    @staticmethod
    def _has_promotion_toggle(patch: ScenarioPatch) -> bool:
        return patch.event is not None and patch.event.promotion is not None

    @staticmethod
    def _has_epidemic_toggle(patch: ScenarioPatch) -> bool:
        return patch.event is not None and patch.event.epidemic is not None

    @staticmethod
    def _has_lead_time_delta(patch: ScenarioPatch) -> bool:
        return (
            patch.replenishment is not None
            and patch.replenishment.lead_time_days_delta is not None
        )

    @staticmethod
    def _has_replenishment_delay(patch: ScenarioPatch) -> bool:
        return (
            patch.replenishment is not None
            and patch.replenishment.actual_delay_days_delta is not None
        )


class ScenarioValidator:
    @staticmethod
    def validate(patch: ScenarioPatch) -> ScenarioPatch:
        if patch.demand and patch.demand.demand_multiplier is not None:
            if patch.demand.demand_multiplier <= 0:
                raise ValueError("Demand multiplier must be positive.")

        if patch.inventory and patch.inventory.safety_stock_multiplier is not None:
            if patch.inventory.safety_stock_multiplier <= 0:
                raise ValueError("Safety stock multiplier must be positive.")

        if patch.event and patch.event.seasonality is not None:
            if patch.event.seasonality.lower() not in VALID_SEASONS:
                raise ValueError(
                    "Invalid seasonality. Use winter, spring, summer, or autumn."
                )

        if patch.replenishment:
            delay = patch.replenishment.actual_delay_days_delta
            if delay is not None and delay < 0:
                raise ValueError(
                    "Replenishment delay days must be zero or positive."
                )

        if patch.planning_window_days is not None and patch.planning_window_days <= 0:
            raise ValueError("Planning window days must be positive.")

        return patch

    @staticmethod
    def validate_against_state(
        patch: ScenarioPatch,
        state: SimulationState,
    ) -> None:
        if patch.inventory and patch.inventory.current_stock_delta is not None:
            resulting_stock = (
                state.inventory.current_stock
                + patch.inventory.current_stock_delta
            )
            if resulting_stock < 0:
                raise ValueError(
                    f"Inventory cannot become negative "
                    f"(current={state.inventory.current_stock}, "
                    f"delta={patch.inventory.current_stock_delta})."
                )

        if (
            patch.replenishment
            and patch.replenishment.lead_time_days_delta is not None
            and state.replenishment.has_incoming_replenishment
            and state.replenishment.lead_time_days is not None
        ):
            resulting_lead_time = (
                state.replenishment.lead_time_days
                + patch.replenishment.lead_time_days_delta
            )
            if resulting_lead_time < 0:
                raise ValueError(
                    "Lead time cannot become negative after the scenario change."
                )


def _infer_types_from_patch(patch: ScenarioPatch) -> list[ScenarioType]:
    types: list[ScenarioType] = []
    if patch.demand and patch.demand.demand_multiplier is not None:
        types.append("demand_change")
    if patch.inventory and patch.inventory.current_stock_delta is not None:
        types.append("inventory_change")
    if patch.event and patch.event.seasonality is not None:
        types.append("seasonality_change")
    if patch.event and patch.event.promotion is not None:
        types.append("promotion_toggle")
    if patch.event and patch.event.epidemic is not None:
        types.append("epidemic_toggle")
    if (
        patch.replenishment
        and patch.replenishment.lead_time_days_delta is not None
    ):
        types.append("lead_time_change")
    if (
        patch.replenishment
        and patch.replenishment.actual_delay_days_delta is not None
    ):
        types.append("replenishment_delay")
    return types


def understand_scenario(
    scenario_text: str,
    state: Optional[SimulationState] = None,
) -> ScenarioUnderstandingResult:
    extraction = _extract_with_llm(scenario_text, state)

    if not extraction.scenario_types:
        extraction.scenario_types = _infer_types_from_patch(
            extraction.patch
        )

    if not extraction.scenario_types:
        return ScenarioUnderstandingResult(
            status="needs_clarification",
            clarification_questions=[
                "Which scenario should be simulated? Supported changes: "
                "demand increase/decrease, inventory increase/decrease, "
                "seasonality change, promotion on/off, epidemic on/off, "
                "lead time increase/decrease, or replenishment delay."
            ],
        )

    questions = ClarificationChecker.check(
        extraction,
        scenario_text,
        state,
    )
    if questions:
        return ScenarioUnderstandingResult(
            status="needs_clarification",
            clarification_questions=questions,
        )

    patch = ScenarioValidator.validate(extraction.patch)
    if state is not None:
        ScenarioValidator.validate_against_state(patch, state)

    return ScenarioUnderstandingResult(
        status="complete",
        patch=patch,
    )
