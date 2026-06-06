"""Coordinate mapping utilities for MVP synthetic model-space coordinates.

This module maps real WGS84 coordinates into a fixed synthetic range while
preserving geometry up to a single global scale factor. It is intentionally
standalone and does not integrate with any service by itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import atan, exp, log, pi, tan
from typing import Iterable, Sequence


# Historical model-space bounds provided by the team.
MODEL_LAT_MIN = -57.01
MODEL_LAT_MAX = -44.88
MODEL_LNG_MIN = 79.24
MODEL_LNG_MAX = 100.85

# WGS84 / spherical Web Mercator constants.
EARTH_RADIUS_M = 6_378_137.0
MAX_MERCATOR_LAT = 85.05112878


@dataclass(frozen=True)
class WGS84Point:
    lat: float
    lng: float


@dataclass(frozen=True)
class MetricPoint:
    x: float
    y: float


@dataclass(frozen=True)
class Bounds:
    min_x: float
    max_x: float
    min_y: float
    max_y: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y


@dataclass(frozen=True)
class CoordinateMapper:
    """Affine mapper between WGS84 and synthetic model-space coordinates.

    Mapping is:
        (lat, lng) -> WebMercator(x, y) -> synthetic(lng, lat)

    The synthetic output intentionally uses:
        synthetic_lat in [MODEL_LAT_MIN, MODEL_LAT_MAX]
        synthetic_lng in [MODEL_LNG_MIN, MODEL_LNG_MAX]
    """

    source_bounds: Bounds
    target_bounds: Bounds
    scale: float
    pad_x: float
    pad_y: float

    def to_synthetic(self, point: WGS84Point) -> WGS84Point:
        metric = wgs84_to_web_mercator(point)
        syn_x = (
            self.target_bounds.min_x
            + (metric.x - self.source_bounds.min_x) * self.scale
            + self.pad_x
        )
        syn_y = (
            self.target_bounds.min_y
            + (metric.y - self.source_bounds.min_y) * self.scale
            + self.pad_y
        )
        return WGS84Point(lat=syn_y, lng=syn_x)

    def to_real_wgs84(self, synthetic: WGS84Point) -> WGS84Point:
        x = (
            self.source_bounds.min_x
            + (
                synthetic.lng
                - self.target_bounds.min_x
                - self.pad_x
            )
            / self.scale
        )
        y = (
            self.source_bounds.min_y
            + (
                synthetic.lat
                - self.target_bounds.min_y
                - self.pad_y
            )
            / self.scale
        )
        return web_mercator_to_wgs84(MetricPoint(x=x, y=y))

    def to_synthetic_many(self, points: Iterable[WGS84Point]) -> list[WGS84Point]:
        return [self.to_synthetic(p) for p in points]

    def to_real_wgs84_many(self, points: Iterable[WGS84Point]) -> list[WGS84Point]:
        return [self.to_real_wgs84(p) for p in points]

    def delivery_mercator_to_model_space(
        self,
        mercator_x: float,
        mercator_y: float,
    ) -> WGS84Point:
        """Delivery.csv Mercator metres (poi_lng, poi_lat) -> model-space lat/lng."""
        return mercator_to_model_space(mercator_x, mercator_y)

    def delivery_mercator_to_cluster(
        self,
        mercator_x: float,
        mercator_y: float,
    ) -> WGS84Point:
        """Delivery.csv Mercator metres -> real China WGS84 for clustering/OSRM."""
        return self.to_real_wgs84(
            mercator_to_model_space(mercator_x, mercator_y)
        )

    def delivery_mercator_to_model_space_batch(
        self,
        mercator_x: Sequence[float],
        mercator_y: Sequence[float],
    ) -> tuple[list[float], list[float]]:
        """Batch Mercator (poi_lng, poi_lat) -> (model_lat, model_lng)."""
        return mercator_to_model_space_batch(mercator_x, mercator_y)

    def delivery_mercator_to_cluster_batch(
        self,
        mercator_x: Sequence[float],
        mercator_y: Sequence[float],
    ) -> tuple[list[float], list[float]]:
        """Batch Mercator (poi_lng, poi_lat) -> (lat, lng) in real China WGS84."""
        model_lats, model_lngs = mercator_to_model_space_batch(mercator_x, mercator_y)
        real = self.to_real_wgs84_many(
            WGS84Point(lat=lat, lng=lng)
            for lat, lng in zip(model_lats, model_lngs)
        )
        return [p.lat for p in real], [p.lng for p in real]


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def wgs84_to_web_mercator(point: WGS84Point) -> MetricPoint:
    """Convert WGS84 degrees to spherical Web Mercator meters."""
    lat = _clamp(point.lat, -MAX_MERCATOR_LAT, MAX_MERCATOR_LAT)
    x = EARTH_RADIUS_M * point.lng * pi / 180.0
    y = EARTH_RADIUS_M * log(tan(pi / 4.0 + (lat * pi / 180.0) / 2.0))
    return MetricPoint(x=x, y=y)


def web_mercator_to_wgs84(point: MetricPoint) -> WGS84Point:
    """Convert spherical Web Mercator meters back to WGS84 degrees."""
    lng = (point.x / EARTH_RADIUS_M) * 180.0 / pi
    lat = (2.0 * atan(exp(point.y / EARTH_RADIUS_M)) - pi / 2.0) * 180.0 / pi
    return WGS84Point(lat=lat, lng=lng)


def mercator_xy_to_wgs84(x: float, y: float) -> WGS84Point:
    """Convert Web Mercator easting/northing metres to decoded lat/lng degrees."""
    return web_mercator_to_wgs84(MetricPoint(x=x, y=y))


def mercator_to_model_space(mercator_x: float, mercator_y: float) -> WGS84Point:
    """Delivery.csv Mercator metres (poi_lng, poi_lat) -> model-space lat/lng."""
    return mercator_xy_to_wgs84(mercator_x, mercator_y)


def mercator_to_model_space_batch(
    mercator_x: Sequence[float],
    mercator_y: Sequence[float],
) -> tuple[list[float], list[float]]:
    """Batch Mercator (poi_lng, poi_lat) -> (model_lat, model_lng)."""
    import numpy as np

    x_arr = np.asarray(mercator_x, dtype=float)
    y_arr = np.asarray(mercator_y, dtype=float)
    lng = (x_arr / EARTH_RADIUS_M) * 180.0 / pi
    lat = (2.0 * np.arctan(np.exp(y_arr / EARTH_RADIUS_M)) - pi / 2.0) * 180.0 / pi
    return lat.tolist(), lng.tolist()


def compute_bounds(points: Sequence[MetricPoint]) -> Bounds:
    if not points:
        raise ValueError("At least one point is required to compute bounds.")
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    return Bounds(min_x=min(xs), max_x=max(xs), min_y=min(ys), max_y=max(ys))


def build_mapper_from_wgs84_anchors(
    anchors: Sequence[WGS84Point],
    target_lat_min: float = MODEL_LAT_MIN,
    target_lat_max: float = MODEL_LAT_MAX,
    target_lng_min: float = MODEL_LNG_MIN,
    target_lng_max: float = MODEL_LNG_MAX,
) -> CoordinateMapper:
    """Build an isotropic affine mapper from real anchors to target bounds.

    Uses a single scale value for both axes to preserve shape and bearings.
    Distances are preserved up to this constant scale factor.
    """
    if len(anchors) < 2:
        raise ValueError("At least two anchors are required.")

    metric_anchors = [wgs84_to_web_mercator(p) for p in anchors]
    source = compute_bounds(metric_anchors)
    target = Bounds(
        min_x=target_lng_min,
        max_x=target_lng_max,
        min_y=target_lat_min,
        max_y=target_lat_max,
    )

    if source.width <= 0 or source.height <= 0:
        raise ValueError("Anchor bounds are degenerate. Provide spread-out anchors.")
    if target.width <= 0 or target.height <= 0:
        raise ValueError("Target bounds are invalid.")

    scale = min(target.width / source.width, target.height / source.height)
    pad_x = (target.width - source.width * scale) / 2.0
    pad_y = (target.height - source.height * scale) / 2.0

    return CoordinateMapper(
        source_bounds=source,
        target_bounds=target,
        scale=scale,
        pad_x=pad_x,
        pad_y=pad_y,
    )


def default_mvp_city_anchors() -> list[WGS84Point]:
    """Approximate city-center anchors for the requested 5-city MVP setup."""
    return [
        WGS84Point(lat=31.2304, lng=121.4737),  # Shanghai
        WGS84Point(lat=30.2741, lng=120.1551),  # Hangzhou
        WGS84Point(lat=29.5630, lng=106.5516),  # Chongqing
        WGS84Point(lat=43.8378, lng=126.5496),  # Jilin
        WGS84Point(lat=37.4638, lng=121.4479),  # Yantai
    ]


def build_default_mvp_mapper() -> CoordinateMapper:
    """Build mapper using the 5 default city anchors."""
    return build_mapper_from_wgs84_anchors(default_mvp_city_anchors())
