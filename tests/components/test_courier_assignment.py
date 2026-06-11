"""Tests for the shared courier_assignment module."""

from __future__ import annotations

import pytest

from aura_graphdb.courier_assignment import select_courier_for_order
from aura_graphdb.hub_coordinates import NEARBY_HUB_KM


# Chongqing-area WGS84 coords (realistic, a few km apart)
COURIER_A = {"courier_id": "courier-a", "start_lat_wgs84": 29.57, "start_lon_wgs84": 106.55, "city_name": "Chongqing"}
COURIER_B = {"courier_id": "courier-b", "start_lat_wgs84": 29.60, "start_lon_wgs84": 106.58, "city_name": "Chongqing"}
COURIERS = [COURIER_A, COURIER_B]

PICKUP_LAT = 29.57
PICKUP_LON = 106.55
DELIVERY_DAY = "2026-06-13"


def test_tier2_fallback_no_existing_orders():
    """With no same-day orders, nearest courier is selected."""
    chosen, dist_m = select_courier_for_order(
        pickup_lat=PICKUP_LAT,
        pickup_lon=PICKUP_LON,
        delivery_day=DELIVERY_DAY,
        couriers=COURIERS,
        existing_orders=[],
    )
    # courier-a is at same lat/lon as pickup → closest
    assert chosen["courier_id"] == "courier-a"
    assert dist_m < 100  # essentially 0 distance


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


def test_different_day_orders_ignored():
    """Same-day orders from a DIFFERENT day must not trigger consolidation."""
    different_day_stop = {
        "assigned_courier_id": "courier-b",
        "delivery_day": "2026-06-14",  # wrong day
        "receipt_lat_wgs84": PICKUP_LAT + 0.001,
        "receipt_lon_wgs84": PICKUP_LON + 0.001,
        "lat_wgs84": PICKUP_LAT,
        "lon_wgs84": PICKUP_LON,
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
    # distance should be a non-negative float
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
