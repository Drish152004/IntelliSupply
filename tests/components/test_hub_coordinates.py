"""Geo-utility tests — haversine and constants from courier_assignment."""

from __future__ import annotations

from rag.aura_graphdb.courier_assignment import (
    NEARBY_HUB_KM,
    MAX_ORDERS_PER_DAY,
    haversine_distance_m,
)

ML_DEFAULT_DS = 318


def test_ml_default_ds():
    assert ML_DEFAULT_DS == 318


def test_nearby_hub_km_positive():
    assert NEARBY_HUB_KM > 0


def test_haversine_same_point_is_zero():
    assert haversine_distance_m(30.0, 106.5, 30.0, 106.5) == 0.0


def test_haversine_symmetry():
    a_lat, a_lon = 30.0, 106.5
    b_lat, b_lon = 30.01, 106.51
    assert abs(
        haversine_distance_m(a_lat, a_lon, b_lat, b_lon)
        - haversine_distance_m(b_lat, b_lon, a_lat, a_lon)
    ) < 1e-6


def test_haversine_known_distance():
    # Two points ~1 km apart near Chongqing
    d = haversine_distance_m(29.56, 106.55, 29.57, 106.55)
    assert 1000 < d < 1200, f"Expected ~1110 m, got {d:.1f} m"


def test_haversine_chongqing_to_jilin_is_large():
    # Chongqing (29.5°N, 106.5°E) to Jilin (43.8°N, 126.5°E)
    d = haversine_distance_m(29.5, 106.5, 43.8, 126.5)
    assert d > 2_000_000, f"Expected >2000 km inter-city, got {d:.0f} m"


def test_max_orders_per_day():
    assert MAX_ORDERS_PER_DAY == 20
