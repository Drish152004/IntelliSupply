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
