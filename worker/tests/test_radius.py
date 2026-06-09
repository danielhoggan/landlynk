"""Radius catchment geometry."""

from __future__ import annotations

from shapely.geometry import shape

from landlynk_worker.pipeline.radius import radius_polygon


def test_radius_polygon_is_a_closed_area_around_the_point():
    # A 1.5 km radius around central London. The point sits inside, and the
    # bounds span roughly 3 km (about 0.04 deg lat), not the whole city.
    geo = radius_polygon(51.5074, -0.1278, 1.5)
    poly = shape(geo)
    assert poly.is_valid
    assert poly.contains(shape({"type": "Point", "coordinates": [-0.1278, 51.5074]}))
    minx, miny, maxx, maxy = poly.bounds
    assert 0.02 < (maxy - miny) < 0.06  # ~3 km north-south


def test_larger_radius_covers_more_area():
    small = shape(radius_polygon(52.2, 0.12, 1.0)).area
    large = shape(radius_polygon(52.2, 0.12, 5.0)).area
    assert large > small
