"""Spatial intersect of boundary geometries against the drive-time isochrone.

Pure geometry, no I/O, so it is testable against fixture geometries with known
overlaps (house-standards.md, testing). In production the same proportions are
computed in PostGIS; this module is the reference implementation and the unit
of test, and is used directly for in-memory geometry.

Areas below a configurable overlap threshold are discarded to avoid noise from
clipped edges (SCOPING.md Section 7, step 3).
"""

from __future__ import annotations

from dataclasses import dataclass

from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry


@dataclass(frozen=True)
class AreaGeometry:
    area_code: str
    area_type: str  # "MSOA" or "LA"
    geometry: BaseGeometry


@dataclass(frozen=True)
class IntersectResult:
    area_code: str
    area_type: str
    # Proportion of the area's own footprint that falls inside the isochrone, 0..1.
    proportion_inside: float


def proportion_inside(area: BaseGeometry, isochrone: BaseGeometry) -> float:
    """Fraction of ``area`` covered by ``isochrone``, in 0..1.

    Returns 0.0 for an empty or zero-area geometry rather than raising, so a
    degenerate boundary cannot crash a run.
    """
    if area.is_empty or area.area == 0:
        return 0.0
    overlap = area.intersection(isochrone).area
    return max(0.0, min(1.0, overlap / area.area))


def intersect_catchment(
    areas: list[AreaGeometry],
    isochrone: BaseGeometry,
    overlap_threshold: float,
) -> list[IntersectResult]:
    """Return areas overlapping the isochrone above the threshold, weighted.

    Results are sorted by proportion inside, descending, so the most fully
    covered areas lead.
    """
    results: list[IntersectResult] = []
    for area in areas:
        prop = proportion_inside(area.geometry, isochrone)
        if prop >= overlap_threshold:
            results.append(
                IntersectResult(
                    area_code=area.area_code,
                    area_type=area.area_type,
                    proportion_inside=prop,
                )
            )
    results.sort(key=lambda r: r.proportion_inside, reverse=True)
    return results


def area_geometry_from_geojson(
    area_code: str, area_type: str, geojson_geometry: dict
) -> AreaGeometry:
    """Build an :class:`AreaGeometry` from a GeoJSON geometry dict."""
    return AreaGeometry(
        area_code=area_code,
        area_type=area_type,
        geometry=shape(geojson_geometry),
    )
