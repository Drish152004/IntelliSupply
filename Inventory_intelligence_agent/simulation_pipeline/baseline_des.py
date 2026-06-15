from __future__ import annotations

from state_models import ScenarioState
from simulation_models import SimulationDay, SimulationResult
from world_models import SimulatedWorld


def _replenishment_quantity(scenario: ScenarioState) -> float | None:
    replenishment = scenario.replenishment
    if not replenishment.has_incoming_replenishment:
        return None
    if replenishment.quantity_ordered is None:
        return None
    return float(replenishment.quantity_ordered)


def simulate_world(
    scenario: ScenarioState,
    world: SimulatedWorld,
) -> SimulationResult:
    horizon = scenario.planning_window_days
    if len(world.daily_demand) != horizon:
        raise ValueError(
            "daily_demand length "
            f"({len(world.daily_demand)}) must match planning_window_days ({horizon})"
        )

    safety_stock = scenario.inventory.safety_stock
    quantity_ordered = _replenishment_quantity(scenario)
    arrival_day = world.replenishment_arrival_day

    inventory = float(scenario.inventory.current_stock)
    minimum_inventory = inventory
    shortage_quantity = 0.0
    stockout_occurred = False
    stockout_day: int | None = None
    days_below_safety_stock = 0
    daily_log: list[SimulationDay] = []

    if (
        quantity_ordered is not None
        and arrival_day is not None
        and arrival_day <= 0
    ):
        inventory += quantity_ordered

    for day in range(horizon):
        starting_inventory = inventory
        replenishment_received = 0.0

        if (
            quantity_ordered is not None
            and arrival_day is not None
            and arrival_day > 0
            and day == arrival_day
        ):
            inventory += quantity_ordered
            replenishment_received = quantity_ordered

        demand = world.daily_demand[day]
        inventory -= demand

        day_stockout = False
        if inventory < 0:
            shortage_quantity += abs(inventory)
            inventory = 0.0
            day_stockout = True
            if not stockout_occurred:
                stockout_occurred = True
                stockout_day = day

        minimum_inventory = min(minimum_inventory, inventory)
        below_safety_stock = inventory < safety_stock
        if below_safety_stock:
            days_below_safety_stock += 1

        daily_log.append(
            SimulationDay(
                day=day,
                starting_inventory=starting_inventory,
                demand=demand,
                replenishment_received=replenishment_received,
                ending_inventory=inventory,
                below_safety_stock=below_safety_stock,
                stockout_occurred=day_stockout,
            )
        )

    return SimulationResult(
        world_id=world.world_id,
        ending_inventory=inventory,
        minimum_inventory=minimum_inventory,
        stockout_occurred=stockout_occurred,
        stockout_day=stockout_day,
        shortage_quantity=shortage_quantity,
        safety_stock_breached=days_below_safety_stock > 0,
        days_below_safety_stock=days_below_safety_stock,
        daily_log=daily_log,
    )


def simulate_worlds(
    scenario: ScenarioState,
    worlds: list[SimulatedWorld],
) -> list[SimulationResult]:
    return [simulate_world(scenario, world) for world in worlds]
