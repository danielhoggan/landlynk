"""Radius catchment geometry.

An alternative to the drive-time isochrone: a circular buffer of a given radius
around the geocoded point. In dense cities (London especially) drive times are
noisy and people move short distances, so a straight radius is often the better
catchment. No external provider is called, so it is free and fast.

The buffer is computed in British National Grid (EPSG:27700, metres) so the
radius is a true ground distance, then reprojected to WGS84 for the rest of the
pipeline, which speaks GeoJSON in lon/lat like the isochrone path.
"""

from __future__ import annotations

from functools import lru_cache

from shapely.geometry import Point, mapping
from shapely.ops import transform


@lru_cache(maxsize=2)
def _transformers() -> tuple:
    from pyproj import Transformer

    to_bng = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)
    to_wgs = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
    return to_bng, to_wgs


def radius_polygon(lat: float, lng: float, radius_km: float) -> dict:
    """A GeoJSON Polygon approximating a circle of radius_km around lat/lng."""
    to_bng, to_wgs = _transformers()
    x, y = to_bng.transform(lng, lat)
    circle = Point(x, y).buffer(max(radius_km, 0.01) * 1000.0, quad_segs=64)
    circle_wgs = transform(to_wgs.transform, circle)
    return mapping(circle_wgs)
