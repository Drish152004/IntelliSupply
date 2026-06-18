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


def _find_latest_inventory_row_index(
    df: pd.DataFrame,
    *,
    hub_id: str | int,
    product_id: str,
    category: str,
    simulation_date: str,
) -> int | None:
    mask = (
        (df["hub_id"].astype(str) == str(hub_id))
        & (df["product_id"] == product_id)
        & (df["category"] == category)
        & (df["health_date"] <= simulation_date)
    )
    candidates = df[mask]
    if candidates.empty:
        return None
    return int(candidates.sort_values("health_date", ascending=False).index[0])


def _apply_current_stock_delta(
    df: pd.DataFrame,
    row_index: int,
    delta: int,
) -> None:
    current_stock = int(df.loc[row_index, "current_stock"])
    new_stock = current_stock + delta
    if new_stock < 0:
        raise ValueError(
            f"current_stock would become negative ({new_stock}) for hub "
            f"{df.loc[row_index, 'hub_id']}"
        )
    df.loc[row_index, "current_stock"] = new_stock
    if "threshold_quantity" in df.columns and "threshold_gap" in df.columns:
        threshold = float(df.loc[row_index, "threshold_quantity"])
        df.loc[row_index, "threshold_gap"] = max(0.0, threshold - float(new_stock))


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

        transfer_quantity = int(decision.parameters.get("transfer_quantity") or 0)
        if transfer_quantity <= 0:
            return ActionExecutionResult(
                decision=decision,
                success=False,
                execution_details={"error": "transfer_quantity must be positive."},
            )

        df = pd.read_csv(INVENTORY_HEALTH_CSV)
        source_index = _find_latest_inventory_row_index(
            df,
            hub_id=source_hub,
            product_id=scenario.product_id,
            category=scenario.category,
            simulation_date=scenario.simulation_date,
        )
        target_index = _find_latest_inventory_row_index(
            df,
            hub_id=target_hub,
            product_id=scenario.product_id,
            category=scenario.category,
            simulation_date=scenario.simulation_date,
        )
        if source_index is None or target_index is None:
            return ActionExecutionResult(
                decision=decision,
                success=False,
                execution_details={
                    "error": "No inventory record found for source or target hub.",
                    "source_hub_id": source_hub,
                    "target_hub_id": target_hub,
                    "source_row_found": source_index is not None,
                    "target_row_found": target_index is not None,
                },
            )

        source_before = df.loc[source_index].to_dict()
        target_before = df.loc[target_index].to_dict()
        if int(source_before["current_stock"]) < transfer_quantity:
            return ActionExecutionResult(
                decision=decision,
                success=False,
                execution_details={
                    "error": "Insufficient stock at source hub for transfer.",
                    "source_hub_id": source_hub,
                    "source_current_stock": int(source_before["current_stock"]),
                    "transfer_quantity": transfer_quantity,
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
                f" ({transfer_quantity} units)."
            ),
        }

        try:
            from services.orders import create_shipment

            result = create_shipment(payload)
            if not result.get("success"):
                return ActionExecutionResult(
                    decision=decision,
                    success=False,
                    execution_details={
                        "shipment_payload": payload,
                        "shipment_result": result,
                    },
                )

            _apply_current_stock_delta(df, source_index, -transfer_quantity)
            _apply_current_stock_delta(df, target_index, transfer_quantity)
            df.to_csv(INVENTORY_HEALTH_CSV, index=False)

            source_after = df.loc[source_index].to_dict()
            target_after = df.loc[target_index].to_dict()
            return ActionExecutionResult(
                decision=decision,
                success=True,
                execution_details={
                    "shipment_payload": payload,
                    "shipment_result": result,
                    "transfer_quantity": transfer_quantity,
                    "before_state": {
                        "source": source_before,
                        "target": target_before,
                    },
                    "after_state": {
                        "source": source_after,
                        "target": target_after,
                    },
                },
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
        row_index = _find_latest_inventory_row_index(
            df,
            hub_id=scenario.hub_id,
            product_id=scenario.product_id,
            category=scenario.category,
            simulation_date=scenario.simulation_date,
        )
        if row_index is None:
            return ActionExecutionResult(
                decision=decision,
                success=False,
                execution_details={"error": "No inventory record found for safety stock update."},
            )
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
