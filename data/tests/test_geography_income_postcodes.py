"""Geography, income and postcode transforms."""

from __future__ import annotations

import json

from loaders.base import SourceSpec
from loaders.geography import BoundariesLoader, GeoLookupLoader
from loaders.income import IncomeLoader
from loaders.postcodes import PostcodeLoader, normalise_postcode

SPEC = SourceSpec("t", "provider", "OGL", "v", "url")


def test_geo_lookup_transform_dedups_by_oa():
    raw = [
        {
            "OA21CD": "E00000001",
            "MSOA21CD": "E02000001",
            "MSOA21NM": "Area A",
            "LAD21CD": "E09000001",
            "LAD21NM": "LA A",
        },
        # Duplicate OA is dropped.
        {
            "OA21CD": "E00000001",
            "MSOA21CD": "E02000001",
            "MSOA21NM": "Area A",
            "LAD21CD": "E09000001",
            "LAD21NM": "LA A",
        },
    ]
    rows = GeoLookupLoader(SPEC, "lookup.csv").transform(raw)
    assert len(rows) == 1
    assert rows[0]["msoa_code"] == "E02000001"


def test_boundaries_transform_extracts_code_and_geometry():
    raw = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"MSOA21CD": "E02000001", "MSOA21NM": "Area A"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]],
                },
            }
        ],
    }
    loader = BoundariesLoader(SPEC, "b.geojson", area_type="MSOA")
    rows = loader.transform(raw)
    assert rows[0]["area_code"] == "E02000001"
    assert rows[0]["area_type"] == "MSOA"
    # Geometry is serialised JSON ready for ST_GeomFromGeoJSON.
    assert json.loads(rows[0]["geom"])["type"] == "Polygon"


def test_income_transform_detects_columns():
    raw = [
        {
            "MSOA code": "E02000001",
            "Net annual income (mean)": "52,000",
            "Net annual income (median)": "48,000",
        }
    ]
    rows = IncomeLoader(SPEC, "income.csv").transform(raw)
    assert rows[0]["mean_income"] == 52000.0
    assert rows[0]["median_income"] == 48000.0


def test_income_suppressed_value_is_none():
    raw = [{"MSOA code": "E1", "Net annual income (mean)": ":"}]
    rows = IncomeLoader(SPEC, "i.csv").transform(raw)
    assert rows[0]["mean_income"] is None


def test_normalise_postcode():
    assert normalise_postcode("ip14 1aa") == "IP141AA"


def test_postcode_transform_converts_grid_to_wgs84():
    # CodePoint Open style rows: postcode, quality, easting, northing, ...
    raw = [
        ["IP14 1AA", "10", "606457", "258755", "extra"],
        ["ZZ0 0ZZ", "90", "0", "0"],  # no grid reference, skipped
    ]
    rows = PostcodeLoader(SPEC, "cp.csv").transform(raw)
    assert len(rows) == 1
    point = json.loads(rows[0]["geom"])
    assert point["type"] == "Point"
    lng, lat = point["coordinates"]
    assert 51.5 < lat < 52.5  # Suffolk-ish latitude
    assert 0.5 < lng < 1.5
