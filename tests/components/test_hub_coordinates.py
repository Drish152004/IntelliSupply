"""Hub coordinate utility tests (seed-time conversions only)."""

from __future__ import annotations

from aura_graphdb.hub_coordinates import (
    ML_DEFAULT_DS,
    NEARBY_HUB_KM,
    haversine_distance_m,
    hub_model_to_wgs84,
)


def test_ml_default_ds():
    assert ML_DEFAULT_DS == 318


def test_nearby_hub_km_positive():
    assert NEARBY_HUB_KM > 0


def test_hub_model_to_wgs84_produces_china_range():
    # Chongqing Hub_2 model-space coords from Supabase/Aura seed data.
    lat, lon = hub_model_to_wgs84(-56.6221630006881, 80.0005647345831)
    assert 20 <= lat <= 45
    assert 100 <= lon <= 130


def test_haversine_after_hub_conversion_is_local():
    from_lat, from_lon = hub_model_to_wgs84(-56.6221630006881, 80.0005647345831)
    # A real WGS84 point in Chongqing area
    courier_lat, courier_lon = 30.027772, 101.702724
    distance_m = haversine_distance_m(courier_lat, courier_lon, from_lat, from_lon)
    assert distance_m < 2_000_000


def test_jilin_hub_converts_to_wgs84():
    # Jilin Hub_14 model-space coords
    lat, lon = hub_model_to_wgs84(-45.4467927208657, 100.070421480252)
    assert lat > 40, f"Expected Jilin WGS84 lat > 40, got {lat}"
    assert lon > 120, f"Expected Jilin WGS84 lon > 120, got {lon}"


def test_haversine_symmetry():
    a_lat, a_lon = 30.0, 106.5
    b_lat, b_lon = 30.01, 106.51
    assert abs(
        haversine_distance_m(a_lat, a_lon, b_lat, b_lon)
        - haversine_distance_m(b_lat, b_lon, a_lat, a_lon)
    ) < 1e-6
