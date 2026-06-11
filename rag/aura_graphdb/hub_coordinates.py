"""Hub coordinate utilities."""

from __future__ import annotations

import math
from functools import lru_cache

from ml_services.coordinate_mapping import (
    EARTH_RADIUS_M,
    WGS84Point,
    build_default_mvp_mapper,
)

# Legacy ML shard index stored on Order/RoutePrediction nodes; not used for ops day filtering.
ML_DEFAULT_DS = 318

# Radius used to check if a courier already has a nearby stop on the same delivery day.
NEARBY_HUB_KM = 5.0


@lru_cache(maxsize=1)
def _mapper():
    return build_default_mvp_mapper()


def hub_model_to_wgs84(model_lat: float, model_lon: float) -> tuple[float, float]:
    """Convert hub latitude/longitude from model-space to real WGS84 degrees.

    Called only at seed time (load_hubs_to_aura). Never called on request paths.
    """
    point = _mapper().to_real_wgs84(
        WGS84Point(lat=float(model_lat), lng=float(model_lon)),
    )
    return point.lat, point.lng


def haversine_distance_m(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Great-circle distance in metres between two WGS84 points."""
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    return float(2 * EARTH_RADIUS_M * math.asin(math.sqrt(a)))
