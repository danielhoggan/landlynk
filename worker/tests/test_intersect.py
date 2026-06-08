"""Spatial intersect tested against fixture geometries with known overlaps.

(house-standards.md, testing.)
"""

from __future__ import annotations

from shapely.geometry import box

from landlynk_worker.pipeline.intersect import (
    AreaGeometry,
    area_geometry_from_geojson,
    intersect_catchment,
    proportion_inside,
)


def test_proportion_inside_full_overlap():
    area = box(0, 0, 10, 10)
    isochrone = box(-5, -5, 15, 15)  # fully contains the area
    assert proportion_inside(area, isochrone) == 1.0


def test_proportion_inside_half_overlap():
    area = box(0, 0, 10, 10)
    isochrone = box(0, 0, 5, 10)  # covers exactly the left half
    assert proportion_inside(area, isochrone) == 0.5


def test_proportion_inside_no_overlap():
    area = box(0, 0, 10, 10)
    isochrone = box(20, 20, 30, 30)
    assert proportion_inside(area, isochrone) == 0.0


def test_proportion_inside_empty_area_is_zero():
    empty = box(0, 0, 0, 0)  # degenerate, zero area
    isochrone = box(-1, -1, 1, 1)
    assert proportion_inside(empty, isochrone) == 0.0


def test_intersect_filters_below_threshold_and_sorts():
    isochrone = box(0, 0, 10, 10)
    areas = [
        AreaGeometry("FULL", "MSOA", box(0, 0, 10, 10)),  # 1.0 inside
        AreaGeometry("HALF", "MSOA", box(5, 0, 15, 10)),  # 0.5 inside
        AreaGeometry("EDGE", "MSOA", box(9, 0, 19, 10)),  # 0.1 inside
        AreaGeometry("OUT", "MSOA", box(50, 50, 60, 60)),  # 0.0 inside
    ]

    results = intersect_catchment(areas, isochrone, overlap_threshold=0.2)
    codes = [r.area_code for r in results]

    # EDGE (0.1) and OUT (0.0) are below the 0.2 threshold and dropped.
    assert codes == ["FULL", "HALF"]
    # Sorted by proportion inside, descending.
    assert results[0].proportion_inside == 1.0
    assert results[1].proportion_inside == 0.5


def test_intersect_threshold_is_inclusive():
    isochrone = box(0, 0, 10, 10)
    areas = [AreaGeometry("HALF", "MSOA", box(5, 0, 15, 10))]
    results = intersect_catchment(areas, isochrone, overlap_threshold=0.5)
    assert [r.area_code for r in results] == ["HALF"]


def test_area_geometry_from_geojson():
    geojson = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]],
    }
    area = area_geometry_from_geojson("E02000001", "MSOA", geojson)
    assert area.area_code == "E02000001"
    assert area.geometry.area == 100.0
