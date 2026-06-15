from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class SimulatedWorld:
    world_id: int
    daily_demand: list[float]
    replenishment_arrival_day: Optional[int]
