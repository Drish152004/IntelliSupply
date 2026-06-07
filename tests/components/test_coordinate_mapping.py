"""Coordinate mapping smoke tests (replaces root test_mapper.py)."""

from __future__ import annotations

from ml_services.coordinate_mapping import WGS84Point, build_default_mvp_mapper


def test_default_mapper_to_synthetic():
    mapper = build_default_mvp_mapper()
    synthetic = mapper.to_synthetic(WGS84Point(lat=31.2304, lng=121.4737))
    assert synthetic.lat is not None
    assert synthetic.lng is not None


def test_round_trip_approximate():
    mapper = build_default_mvp_mapper()
    original = WGS84Point(lat=31.2304, lng=121.4737)
    synthetic = mapper.to_synthetic(original)
    restored = mapper.to_real_wgs84(synthetic)
    assert abs(restored.lat - original.lat) < 0.5
    assert abs(restored.lng - original.lng) < 0.5
