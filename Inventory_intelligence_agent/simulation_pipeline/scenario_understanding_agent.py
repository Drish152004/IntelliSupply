# scenario_understanding_agent.py

import json
import os
import re
from typing import Any, Optional

from groq import Groq

from scenario_models import (
    ClarificationPrompt,
    DemandPatch,
    EventPatch,
    InventoryPatch,
    ReplenishmentPatch,
    ScenarioExtraction,
    ScenarioPatch,
    ScenarioUnderstandingResult,
    ScenarioType,
)
from state_models import SimulationState

VALID_SEASONS = frozenset({"winter", "spring", "summer", "autumn"})
SUPPORTED_SCENARIO_TYPES = frozenset({
    "demand_change",
    "inventory_change",
    "seasonality_change",
    "promotion_toggle",
    "epidemic_toggle",
    "lead_time_change",
    "replenishment_delay",
})
DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"

_client: Optional[Groq] = None

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
- When the user combines multiple changes in one question, populate all relevant patch
  sections and list every detected type in scenario_types.

Supported scenario types (list each one detected in scenario_types):
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
patch: { "demand": { "demand_multiplier": 1.25 } }

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


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(
            api_key=os.environ.get("GROQ_API_KEY"),
        )
    return _client


def _get_groq_model() -> str:
    return os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)


def merge_patch(base: ScenarioPatch, updates: ScenarioPatch) -> ScenarioPatch:
    merged = base.model_dump()
    update_data = updates.model_dump(exclude_none=True)
    for key, value in update_data.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return ScenarioPatch.model_validate(merged)


def parse_percent_or_multiplier(raw: str) -> float:
    text = raw.strip()
    if text.endswith("%"):
        pct = float(text[:-1].strip())
        multiplier = 1.0 + (pct / 100.0)
    else:
        value = float(text)
        if value > 5:
            multiplier = 1.0 + (value / 100.0)
        else:
            multiplier = value
    if multiplier <= 0:
        raise ValueError("Demand multiplier must be positive.")
    return multiplier


def parse_signed_int(raw: str) -> int:
    return int(raw.strip())


def parse_positive_int(raw: str) -> int:
    value = int(raw.strip())
    if value < 0:
        raise ValueError("Value must be zero or positive.")
    return value


def parse_boolean(raw: str) -> bool:
    text = raw.strip().lower()
    if text in {"on", "true", "yes", "1"}:
        return True
    if text in {"off", "false", "no", "0"}:
        return False
    raise ValueError("Use on/off or true/false.")


def parse_season(raw: str) -> str:
    season = raw.strip().lower()
    if season not in VALID_SEASONS:
        raise ValueError("Invalid season. Use winter, spring, summer, or autumn.")
    return season


def apply_clarification_answers(
    patch: ScenarioPatch,
    scenario_types: list[ScenarioType],
    answers: dict[str, str],
) -> tuple[ScenarioPatch, list[ScenarioType]]:
    updated_types = list(scenario_types)
    updates: dict[str, Any] = {}

    if "scenario_type" in answers:
        chosen = answers["scenario_type"].strip()
        if chosen not in SUPPORTED_SCENARIO_TYPES:
            raise ValueError(f"Unsupported scenario type: {chosen}")
        updated_types = [chosen]  # type: ignore[list-item]

    if "demand_multiplier" in answers:
        multiplier = parse_percent_or_multiplier(answers["demand_multiplier"])
        updates["demand"] = DemandPatch(demand_multiplier=multiplier)

    if "inventory_delta" in answers:
        updates["inventory"] = InventoryPatch(
            current_stock_delta=parse_signed_int(answers["inventory_delta"]),
        )

    if "seasonality" in answers:
        event_data = dict(updates.get("event") or {})
        event_data["seasonality"] = parse_season(answers["seasonality"])
        updates["event"] = event_data

    if "promotion" in answers:
        event_data = dict(updates.get("event") or {})
        event_data["promotion"] = parse_boolean(answers["promotion"])
        updates["event"] = event_data

    if "epidemic" in answers:
        event_data = dict(updates.get("event") or {})
        event_data["epidemic"] = parse_boolean(answers["epidemic"])
        updates["event"] = event_data

    if "lead_time_delta" in answers:
        updates["replenishment"] = ReplenishmentPatch(
            lead_time_days_delta=parse_signed_int(answers["lead_time_delta"]),
        )

    if "replenishment_delay" in answers:
        updates["replenishment"] = ReplenishmentPatch(
            actual_delay_days_delta=parse_positive_int(answers["replenishment_delay"]),
        )

    if "replenishment_intent" in answers:
        intent = answers["replenishment_intent"].strip()
        if intent == "cancel":
            updated_types = []
        elif intent in SUPPORTED_SCENARIO_TYPES:
            updated_types = [intent]  # type: ignore[list-item]
        else:
            raise ValueError("Invalid replenishment intent choice.")

    patch_updates = ScenarioPatch.model_validate(updates)
    return merge_patch(patch, patch_updates), updated_types


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
        scenario_types: list[ScenarioType],
        scenario_text: str,
    ) -> set[ScenarioType]:
        types = set(scenario_types)
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
        patch: ScenarioPatch,
        scenario_types: list[ScenarioType],
        scenario_text: str,
        state: Optional[SimulationState] = None,
    ) -> list[ClarificationPrompt]:
        inferred = cls._infer_scenario_types(scenario_types, scenario_text)
        prompts: list[ClarificationPrompt] = []

        if not inferred:
            prompts.append(
                ClarificationPrompt(
                    field_id="scenario_type",
                    question=(
                        "Which scenario should be simulated? "
                        "(demand change, inventory change, seasonality, promotion, "
                        "epidemic, lead time, or replenishment delay)"
                    ),
                )
            )
            return prompts

        if "demand_change" in inferred and not cls._has_demand_magnitude(patch):
            prompts.append(
                ClarificationPrompt(
                    field_id="demand_multiplier",
                    question=(
                        "By how much should demand change? "
                        "(e.g. 25% or 1.25 for +25%)"
                    ),
                )
            )

        if "inventory_change" in inferred and not cls._has_inventory_magnitude(patch):
            prompts.append(
                ClarificationPrompt(
                    field_id="inventory_delta",
                    question=(
                        "By how many units should inventory change? "
                        "(e.g. +500 or -200)"
                    ),
                )
            )

        if "seasonality_change" in inferred and not cls._has_seasonality(patch):
            prompts.append(
                ClarificationPrompt(
                    field_id="seasonality",
                    question="Which season? (winter, spring, summer, or autumn)",
                )
            )

        if "promotion_toggle" in inferred and not cls._has_promotion_toggle(patch):
            prompts.append(
                ClarificationPrompt(
                    field_id="promotion",
                    question="Should promotion be on or off?",
                )
            )

        if "epidemic_toggle" in inferred and not cls._has_epidemic_toggle(patch):
            prompts.append(
                ClarificationPrompt(
                    field_id="epidemic",
                    question="Should the epidemic flag be on or off?",
                )
            )

        if "lead_time_change" in inferred and not cls._has_lead_time_delta(patch):
            prompts.append(
                ClarificationPrompt(
                    field_id="lead_time_delta",
                    question="By how many days should lead time change? (e.g. +3 or -2)",
                )
            )

        if (
            "replenishment_delay" in inferred
            and not cls._has_replenishment_delay(patch)
        ):
            prompts.append(
                ClarificationPrompt(
                    field_id="replenishment_delay",
                    question="By how many days should replenishment be delayed?",
                )
            )

        if (
            state is not None
            and not state.replenishment.has_incoming_replenishment
            and (
                "replenishment_delay" in inferred
                or "lead_time_change" in inferred
            )
        ):
            prompts.append(
                ClarificationPrompt(
                    field_id="replenishment_intent",
                    question=(
                        "There is no incoming replenishment order. "
                        "Did you mean lead time change, replenishment delay, or cancel?"
                    ),
                )
            )

        return prompts

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


def _needs_clarification_result(
    patch: ScenarioPatch,
    scenario_types: list[ScenarioType],
    prompts: list[ClarificationPrompt],
) -> ScenarioUnderstandingResult:
    return ScenarioUnderstandingResult(
        status="needs_clarification",
        partial_patch=patch,
        scenario_types=scenario_types,
        clarification_prompts=prompts,
        clarification_questions=[prompt.question for prompt in prompts],
    )


def _finalize_patch(
    patch: ScenarioPatch,
    state: Optional[SimulationState],
) -> ScenarioUnderstandingResult:
    patch = ScenarioValidator.validate(patch)
    if state is not None:
        ScenarioValidator.validate_against_state(patch, state)

    return ScenarioUnderstandingResult(
        status="complete",
        patch=patch,
        scenario_types=_infer_types_from_patch(patch),
    )


def understand_scenario(
    scenario_text: str,
    state: Optional[SimulationState] = None,
    *,
    partial_patch: Optional[ScenarioPatch] = None,
    scenario_types: Optional[list[ScenarioType]] = None,
    clarification_answers: Optional[dict[str, str]] = None,
) -> ScenarioUnderstandingResult:
    if partial_patch is not None and clarification_answers is not None:
        types = list(scenario_types or [])
        patch, types = apply_clarification_answers(
            partial_patch,
            types,
            clarification_answers,
        )
        if not types:
            return ScenarioUnderstandingResult(
                status="needs_clarification",
                partial_patch=patch,
                scenario_types=[],
                clarification_prompts=[
                    ClarificationPrompt(
                        field_id="scenario_type",
                        question="Which scenario should be simulated?",
                    )
                ],
                clarification_questions=["Which scenario should be simulated?"],
            )

        prompts = ClarificationChecker.check(
            patch,
            types,
            scenario_text,
            state,
        )
        if prompts:
            return _needs_clarification_result(patch, types, prompts)

        return _finalize_patch(patch, state)

    extraction = _extract_with_llm(scenario_text, state)

    if not extraction.scenario_types:
        extraction.scenario_types = _infer_types_from_patch(extraction.patch)

    types = list(extraction.scenario_types)
    patch = extraction.patch

    prompts = ClarificationChecker.check(patch, types, scenario_text, state)
    if prompts:
        return _needs_clarification_result(patch, types, prompts)

    return _finalize_patch(patch, state)
