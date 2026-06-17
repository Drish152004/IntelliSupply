from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from decision_models import ActionExecutionResult, Decision, DecisionType, ExecutionDecision
from state_models import ScenarioState

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INVENTORY_HEALTH_CSV = DATA_DIR / "inventory_health_daily.csv"
REPLENISHMENT_ORDERS_CSV = DATA_DIR / "replenishment_orders.csv"
HUBS_CSV = DATA_DIR / "hubs_simple_import.csv"


def _safe_snapshot(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    return value


class ActionExecutor(ABC):
    @abstractmethod
    def execute(self, decision: Decision, scenario: ScenarioState) -> ActionExecutionResult:
        raise NotImplementedError


class ShipmentTransferExecutor(ActionExecutor):
    def __init__(self) -> None:
        self._hubs = pd.read_csv(HUBS_CSV)

    def _hub_name(self, hub_id: str | int) -> str:
        row = self._hubs[self._hubs["hub_id"].astype(str) == str(hub_id)]
        if row.empty:
            return f"Hub {hub_id}"
        return str(row.iloc[0]["hub_name"])

    def _hub_city_id(self, hub_id: str | int) -> int | None:
        row = self._hubs[self._hubs["hub_id"].astype(str) == str(hub_id)]
        if row.empty:
            return None
        return int(row.iloc[0]["city_id"])

    def execute(self, decision: Decision, scenario: ScenarioState) -> ActionExecutionResult:
        source_hub = decision.parameters.get("source_hub_id")
        target_hub = decision.parameters.get("target_hub_id")
        if source_hub is None or target_hub is None:
            return ActionExecutionResult(
                decision=decision,
                success=False,
                execution_details={"error": "Missing source/target hub."},
            )

        source_city_id = self._hub_city_id(source_hub)
        target_city_id = self._hub_city_id(target_hub)
        if source_city_id is None or target_city_id is None:
            return ActionExecutionResult(
                decision=decision,
                success=False,
                execution_details={
                    "error": "Unable to resolve hub city for source or target hub.",
                    "source_hub_id": source_hub,
                    "target_hub_id": target_hub,
                },
            )
        if source_city_id != target_city_id:
            return ActionExecutionResult(
                decision=decision,
                success=False,
                execution_details={
                    "error": (
                        "Inventory transfers require source and target hubs "
                        "in the same city."
                    ),
                    "source_hub_id": source_hub,
                    "target_hub_id": target_hub,
                    "source_city_id": source_city_id,
                    "target_city_id": target_city_id,
                },
            )

        delivery_date = scenario.simulation_date
        try:
            scenario_day = date.fromisoformat(str(scenario.simulation_date))
            today = date.today()
            delivery_date = max(scenario_day, today).isoformat()
        except ValueError:
            delivery_date = date.today().isoformat()

        payload = {
            "from_hub_name": self._hub_name(source_hub),
            "to_hub_name": self._hub_name(target_hub),
            "delivery_date": delivery_date,
            "notes": (
                f"Automated inventory transfer for {scenario.product_id}"
                f" ({int(decision.parameters.get('transfer_quantity') or 0)} units)."
            ),
        }

        try:
            from services.orders import create_shipment

            result = create_shipment(payload)
            return ActionExecutionResult(
                decision=decision,
                success=bool(result.get("success")),
                execution_details={"shipment_payload": payload, "shipment_result": result},
            )
        except Exception as exc:
            return ActionExecutionResult(
                decision=decision,
                success=False,
                execution_details={"shipment_payload": payload, "error": str(exc)},
            )


class SafetyStockExecutor(ActionExecutor):
    def execute(self, decision: Decision, scenario: ScenarioState) -> ActionExecutionResult:
        multiplier = float(decision.parameters.get("safety_stock_multiplier") or 1.0)
        before_value = float(scenario.inventory.safety_stock)
        after_value = before_value * multiplier

        df = pd.read_csv(INVENTORY_HEALTH_CSV)
        mask = (
            (df["hub_id"].astype(str) == str(scenario.hub_id))
            & (df["product_id"] == scenario.product_id)
            & (df["category"] == scenario.category)
            & (df["health_date"] <= scenario.simulation_date)
        )
        candidates = df[mask]
        if candidates.empty:
            return ActionExecutionResult(
                decision=decision,
                success=False,
                execution_details={"error": "No inventory record found for safety stock update."},
            )

        row_index = candidates.sort_values("health_date", ascending=False).index[0]
        before_state = df.loc[row_index].to_dict()
        df.loc[row_index, "safety_stock"] = float(after_value)
        if "threshold_quantity" in df.columns:
            df.loc[row_index, "threshold_quantity"] = float(after_value)
        df.to_csv(INVENTORY_HEALTH_CSV, index=False)
        after_state = df.loc[row_index].to_dict()

        return ActionExecutionResult(
            decision=decision,
            success=True,
            execution_details={
                "before_safety_stock": before_value,
                "after_safety_stock": after_value,
                "before_state": before_state,
                "after_state": after_state,
            },
        )


class ReplenishmentExecutor(ActionExecutor):
    def execute(self, decision: Decision, scenario: ScenarioState) -> ActionExecutionResult:
        df = pd.read_csv(REPLENISHMENT_ORDERS_CSV)
        mask = (
            (df["hub_id"].astype(str) == str(scenario.hub_id))
            & (df["product_id"] == scenario.product_id)
            & (df["category"] == scenario.category)
        )
        candidates = df[mask]
        if candidates.empty:
            return ActionExecutionResult(
                decision=decision,
                success=False,
                execution_details={"error": "No replenishment order found for update."},
            )

        future = candidates[candidates["actual_arrival_date"] >= scenario.simulation_date]
        target_rows = future if not future.empty else candidates
        row_index = target_rows.sort_values("actual_arrival_date", ascending=True).index[0]

        before_state = df.loc[row_index].to_dict()
        if decision.decision_type == DecisionType.EXPEDITE_REPLENISHMENT:
            delta = int(decision.parameters.get("lead_time_reduction_days") or 0)
            lead_time = int(df.loc[row_index, "lead_time_days"])
            delay_days = int(df.loc[row_index, "actual_delay_days"])
            arrival = datetime.fromisoformat(str(df.loc[row_index, "actual_arrival_date"]))

            df.loc[row_index, "lead_time_days"] = max(1, lead_time - delta)
            df.loc[row_index, "actual_delay_days"] = max(0, delay_days - delta)
            df.loc[row_index, "actual_arrival_date"] = (arrival - timedelta(days=delta)).date().isoformat()
            applied = {"expedite_days": delta}
        else:
            delta = int(decision.parameters.get("replenishment_delay_days") or 0)
            delay_days = int(df.loc[row_index, "actual_delay_days"])
            arrival = datetime.fromisoformat(str(df.loc[row_index, "actual_arrival_date"]))

            df.loc[row_index, "actual_delay_days"] = max(0, delay_days + delta)
            df.loc[row_index, "actual_arrival_date"] = (arrival + timedelta(days=delta)).date().isoformat()
            applied = {"delay_days": delta}

        df.to_csv(REPLENISHMENT_ORDERS_CSV, index=False)
        after_state = df.loc[row_index].to_dict()

        return ActionExecutionResult(
            decision=decision,
            success=True,
            execution_details={
                "applied": applied,
                "before_state": before_state,
                "after_state": after_state,
            },
        )


def _executor_for(decision: Decision) -> ActionExecutor | None:
    if decision.decision_type in {
        DecisionType.INVENTORY_TRANSFER,
        DecisionType.INVENTORY_TRANSFER_IN,
        DecisionType.INVENTORY_TRANSFER_OUT,
    }:
        return ShipmentTransferExecutor()
    if decision.decision_type in {
        DecisionType.INCREASE_SAFETY_STOCK,
        DecisionType.REDUCE_SAFETY_STOCK,
    }:
        return SafetyStockExecutor()
    if decision.decision_type in {
        DecisionType.EXPEDITE_REPLENISHMENT,
        DecisionType.DELAY_REPLENISHMENT,
    }:
        return ReplenishmentExecutor()
    return None


def execute_decision(decision: Decision, scenario: ScenarioState) -> ActionExecutionResult:
    executor = _executor_for(decision)
    if executor is None:
        return ActionExecutionResult(
            decision=decision,
            success=False,
            execution_details={"error": "No executor found for decision type."},
        )

    result = executor.execute(decision, scenario)
    result.execution_details["scenario_snapshot"] = _safe_snapshot(scenario)
    return result


def execute_decision_if_auto_approved(
    execution_decision: ExecutionDecision,
    scenario: ScenarioState,
) -> ActionExecutionResult:
    decision = execution_decision.decision
    if execution_decision.status != "AUTO_APPROVED":
        return ActionExecutionResult(
            decision=decision,
            success=False,
            execution_details={
                "skipped": True,
                "status": execution_decision.status,
                "reason": execution_decision.reason,
            },
        )

    return execute_decision(decision, scenario)
