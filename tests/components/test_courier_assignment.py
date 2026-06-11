"""Tests for the shared courier_assignment module."""

from __future__ import annotations

import pytest

from aura_graphdb.courier_assignment import MAX_ORDERS_PER_DAY, select_courier_for_order
from aura_graphdb.hub_coordinates import NEARBY_HUB_KM


# Chongqing-area WGS84 coords (realistic, a few km apart)
COURIER_A = {
    "courier_id": "courier-a",
    "start_lat_wgs84": 29.57,
    "start_lon_wgs84": 106.55,
    "city_name": "Chongqing",
    "hub_name": "Hub_1",
}
COURIER_B = {
    "courier_id": "courier-b",
    "start_lat_wgs84": 29.60,
    "start_lon_wgs84": 106.58,
    "city_name": "Chongqing",
    "hub_name": "Hub_2",
}
COURIERS = [COURIER_A, COURIER_B]

PICKUP_LAT = 29.57
PICKUP_LON = 106.55
DELIVERY_DAY = "2026-06-13"


def test_tier2_fallback_no_existing_orders():
    """With no same-day orders, nearest courier is selected (hub or city-nearest)."""
    chosen, dist_m = select_courier_for_order(
        pickup_lat=PICKUP_LAT,
        pickup_lon=PICKUP_LON,
        delivery_day=DELIVERY_DAY,
        couriers=COURIERS,
        existing_orders=[],
    )
    # courier-a is at same lat/lon as pickup → closest overall
    assert chosen["courier_id"] == "courier-a"
    assert dist_m < 100


def test_tier2_hub_scoped_preferred():
    """When pickup hub matches a courier's hub_name, that courier is preferred over a closer one."""
    # courier-b is farther but assigned to the pickup hub
    courier_nearby = {
        "courier_id": "courier-near",
        "start_lat_wgs84": PICKUP_LAT,
        "start_lon_wgs84": PICKUP_LON,
        "city_name": "Chongqing",
        "hub_name": "Hub_Other",  # NOT the pickup hub
    }
    courier_hub_match = {
        "courier_id": "courier-hub",
        "start_lat_wgs84": 29.60,
        "start_lon_wgs84": 106.60,
        "city_name": "Chongqing",
        "hub_name": "Hub_Pickup",  # matches pickup hub
    }
    chosen, _ = select_courier_for_order(
        pickup_lat=PICKUP_LAT,
        pickup_lon=PICKUP_LON,
        delivery_day=DELIVERY_DAY,
        couriers=[courier_nearby, courier_hub_match],
        existing_orders=[],
        pickup_hub_name="Hub_Pickup",
    )
    assert chosen["courier_id"] == "courier-hub"


def test_tier1_consolidation_prefers_courier_with_nearby_stop():
    """If courier-b already has a stop near pickup, it is preferred over physically closest."""
    nearby_stop = {
        "assigned_courier_id": "courier-b",
        "delivery_day": DELIVERY_DAY,
        "receipt_lat_wgs84": PICKUP_LAT + 0.001,  # ~110 m away — within NEARBY_HUB_KM
        "receipt_lon_wgs84": PICKUP_LON + 0.001,
        "lat_wgs84": PICKUP_LAT,
        "lon_wgs84": PICKUP_LON,
    }
    chosen, dist_m = select_courier_for_order(
        pickup_lat=PICKUP_LAT,
        pickup_lon=PICKUP_LON,
        delivery_day=DELIVERY_DAY,
        couriers=COURIERS,
        existing_orders=[nearby_stop],
    )
    assert chosen["courier_id"] == "courier-b"


def test_tier1_consolidation_skips_courier_at_daily_cap():
    """Consolidation tier must NOT pick a courier who has reached MAX_ORDERS_PER_DAY."""
    # courier-b has a nearby stop but is at the daily cap
    existing_orders = []
    for i in range(MAX_ORDERS_PER_DAY):
        existing_orders.append(
            {
                "assigned_courier_id": "courier-b",
                "delivery_day": DELIVERY_DAY,
                "receipt_lat_wgs84": PICKUP_LAT + 0.001,
                "receipt_lon_wgs84": PICKUP_LON + 0.001,
                "lat_wgs84": PICKUP_LAT,
                "lon_wgs84": PICKUP_LON,
                "order_id": f"ord-{i}",
            }
        )
    chosen, _ = select_courier_for_order(
        pickup_lat=PICKUP_LAT,
        pickup_lon=PICKUP_LON,
        delivery_day=DELIVERY_DAY,
        couriers=COURIERS,
        existing_orders=existing_orders,
    )
    # courier-b is at cap, so courier-a should be picked instead
    assert chosen["courier_id"] == "courier-a"


def test_raises_when_all_couriers_at_cap():
    """Assignment must fail with ValueError when every courier has reached the daily cap."""
    existing_orders = []
    for courier_id in ("courier-a", "courier-b"):
        for i in range(MAX_ORDERS_PER_DAY):
            existing_orders.append(
                {
                    "assigned_courier_id": courier_id,
                    "delivery_day": DELIVERY_DAY,
                    "receipt_lat_wgs84": PICKUP_LAT,
                    "receipt_lon_wgs84": PICKUP_LON,
                    "lat_wgs84": PICKUP_LAT,
                    "lon_wgs84": PICKUP_LON,
                    "order_id": f"ord-{courier_id}-{i}",
                }
            )
    with pytest.raises(ValueError, match="daily order limit"):
        select_courier_for_order(
            pickup_lat=PICKUP_LAT,
            pickup_lon=PICKUP_LON,
            delivery_day=DELIVERY_DAY,
            couriers=COURIERS,
            existing_orders=existing_orders,
        )


def test_different_day_orders_ignored():
    """Orders from a different day must not affect assignment."""
    different_day_stop = {
        "assigned_courier_id": "courier-b",
        "delivery_day": "2026-06-14",  # wrong day
        "receipt_lat_wgs84": PICKUP_LAT + 0.001,
        "receipt_lon_wgs84": PICKUP_LON + 0.001,
        "lat_wgs84": PICKUP_LAT,
        "lon_wgs84": PICKUP_LON,
        "order_id": "ord-other",
    }
    chosen, dist_m = select_courier_for_order(
        pickup_lat=PICKUP_LAT,
        pickup_lon=PICKUP_LON,
        delivery_day=DELIVERY_DAY,
        couriers=COURIERS,
        existing_orders=[different_day_stop],
    )
    # Falls back to nearest courier (courier-a)
    assert chosen["courier_id"] == "courier-a"


def test_far_stop_does_not_trigger_consolidation():
    """A stop far beyond NEARBY_HUB_KM must not cause consolidation."""
    far_stop = {
        "assigned_courier_id": "courier-b",
        "delivery_day": DELIVERY_DAY,
        "receipt_lat_wgs84": PICKUP_LAT + 1.0,  # ~111 km away
        "receipt_lon_wgs84": PICKUP_LON + 1.0,
        "lat_wgs84": PICKUP_LAT + 1.0,
        "lon_wgs84": PICKUP_LON + 1.0,
        "order_id": "ord-far",
    }
    chosen, _ = select_courier_for_order(
        pickup_lat=PICKUP_LAT,
        pickup_lon=PICKUP_LON,
        delivery_day=DELIVERY_DAY,
        couriers=COURIERS,
        existing_orders=[far_stop],
    )
    # No consolidation — nearest courier fallback
    assert chosen["courier_id"] == "courier-a"


def test_returns_distance_in_metres():
    chosen, dist_m = select_courier_for_order(
        pickup_lat=PICKUP_LAT,
        pickup_lon=PICKUP_LON,
        delivery_day=DELIVERY_DAY,
        couriers=COURIERS,
        existing_orders=[],
    )
    assert isinstance(dist_m, float)
    assert dist_m >= 0


def test_single_courier_always_assigned():
    """Even with one courier, assignment must succeed."""
    chosen, dist_m = select_courier_for_order(
        pickup_lat=PICKUP_LAT,
        pickup_lon=PICKUP_LON,
        delivery_day=DELIVERY_DAY,
        couriers=[COURIER_A],
        existing_orders=[],
    )
    assert chosen["courier_id"] == "courier-a"


def test_under_cap_courier_preferred_over_at_cap():
    """Among hub-matched couriers, one under cap must be chosen over one at cap."""
    at_cap_orders = [
        {
            "assigned_courier_id": "courier-a",
            "delivery_day": DELIVERY_DAY,
            "receipt_lat_wgs84": PICKUP_LAT,
            "receipt_lon_wgs84": PICKUP_LON,
            "lat_wgs84": PICKUP_LAT,
            "lon_wgs84": PICKUP_LON,
            "order_id": f"ord-a-{i}",
        }
        for i in range(MAX_ORDERS_PER_DAY)
    ]
    # Both assigned to Hub_1 (same as pickup hub), but courier-a is at cap
    courier_a_hub1 = {**COURIER_A, "hub_name": "Hub_1"}
    courier_b_hub1 = {**COURIER_B, "hub_name": "Hub_1"}
    chosen, _ = select_courier_for_order(
        pickup_lat=PICKUP_LAT,
        pickup_lon=PICKUP_LON,
        delivery_day=DELIVERY_DAY,
        couriers=[courier_a_hub1, courier_b_hub1],
        existing_orders=at_cap_orders,
        pickup_hub_name="Hub_1",
    )
    assert chosen["courier_id"] == "courier-b"
