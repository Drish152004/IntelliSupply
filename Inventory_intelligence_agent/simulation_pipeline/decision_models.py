from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class DecisionType(Enum):
    INVENTORY_TRANSFER = "inventory_transfer"
    INVENTORY_TRANSFER_IN = "inventory_transfer_in"
    INVENTORY_TRANSFER_OUT = "inventory_transfer_out"
    EXPEDITE_REPLENISHMENT = "expedite_replenishment"
    INCREASE_SAFETY_STOCK = "increase_safety_stock"
    REDUCE_SAFETY_STOCK = "reduce_safety_stock"
    DELAY_REPLENISHMENT = "delay_replenishment"


@dataclass
class Decision:
    decision_id: str
    decision_type: DecisionType
    title: str
    rationale: str
    parameters: dict[str, Any]


POLICY_AUTO_APPROVED = "AUTO_APPROVED"
POLICY_APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
POLICY_DISABLED = "DISABLED"
MANUAL_EXECUTED = "MANUAL_EXECUTED"
MANUAL_EXECUTION_FAILED = "MANUAL_EXECUTION_FAILED"

POLICY_TYPE_INVENTORY_TRANSFER = "inventory_transfer"
POLICY_TYPE_SAFETY_STOCK_CHANGE_PCT = "safety_stock_change_pct"
POLICY_TYPE_REPLENISHMENT_ORDER = "replenishment_order"

DECISION_TYPE_TO_POLICY_TYPE: dict[DecisionType, str] = {
    DecisionType.INVENTORY_TRANSFER: POLICY_TYPE_INVENTORY_TRANSFER,
    DecisionType.INVENTORY_TRANSFER_IN: POLICY_TYPE_INVENTORY_TRANSFER,
    DecisionType.INVENTORY_TRANSFER_OUT: POLICY_TYPE_INVENTORY_TRANSFER,
    DecisionType.INCREASE_SAFETY_STOCK: POLICY_TYPE_SAFETY_STOCK_CHANGE_PCT,
    DecisionType.REDUCE_SAFETY_STOCK: POLICY_TYPE_SAFETY_STOCK_CHANGE_PCT,
    DecisionType.EXPEDITE_REPLENISHMENT: POLICY_TYPE_REPLENISHMENT_ORDER,
    DecisionType.DELAY_REPLENISHMENT: POLICY_TYPE_REPLENISHMENT_ORDER,
}


DEFAULT_UTILITY_SCORE_THRESHOLD = 0.5


@dataclass
class AutomationPolicy:
    policy_type: str
    enabled: bool
    auto_execute: bool
    threshold_value: float
    utility_score_threshold: float = DEFAULT_UTILITY_SCORE_THRESHOLD


@dataclass
class ExecutionDecision:
    decision: Decision
    status: str  # AUTO_APPROVED / APPROVAL_REQUIRED / DISABLED
    reason: str
    policy_type: str
    threshold_value: float | None = None
    observed_value: float | None = None
    utility_score_threshold: float | None = None
    observed_utility_score: float | None = None


@dataclass
class ActionExecutionResult:
    decision: Decision
    success: bool
    execution_details: dict[str, Any]
