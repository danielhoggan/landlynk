"""Server-side reference loading: transforms, ArcGIS paging and admin routing."""

from __future__ import annotations

import httpx

from landlynk_worker.refdata import loaders
from landlynk_worker.refdata import transforms as t

# --- pure transforms ---------------------------------------------------------


def test_boundary_rows_extracts_code_name_geometry():
    geojson = {
        "features": [
            {
                "properties": {"MSOA21CD": "E02000001", "MSOA21NM": "Area A"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0, 1], [1, 1], [0, 0]]],
                },
            },
            {"properties": {"MSOA21CD": ""}, "geometry": None},  # skipped
        ]
    }
    rows = loaders._boundary_rows(geojson, "MSOA")
    assert len(rows) == 1
    assert rows[0]["area_code"] == "E02000001"
    assert rows[0]["area_type"] == "MSOA"


def test_demographics_rows_merge_and_suppression():
    age = "geography code,Aged 10 years,Aged 20 years,Aged 90 years and over\nE1,100,200,:\n"
    hh = "geography code,Total: All households,Single family household\nE1,200,120\n"
    rows = loaders._demographics_rows(age, hh, "MSOA")
    row = rows[0]
    assert row["age_0_15"] == 100
    assert row["age_16_34"] == 200
    assert row["age_75_plus"] is None  # the only 75+ value was suppressed
    assert row["family_household_share"] == 120 / 200


def test_tenure_rows_to_shares():
    csv_text = (
        "geography code,Total: All households,Owned: Owns outright,"
        "Owned: Owns with a mortgage or loan,Social rented,Private rented\n"
        "E1,1000,250,400,150,200\n"
    )
    row = loaders._tenure_rows(csv_text, "MSOA")[0]
    assert row["owns_outright"] == 0.25
    assert row["private_rented"] == 0.20


def test_income_rows_detect_columns():
    records = [
        {
            "MSOA code": "E1",
            "Net annual income (mean)": "52,000",
            "Net annual income (median)": "48,000",
        }
    ]
    row = loaders._income_rows(records, "MSOA")[0]
    assert row["mean_income"] == 52000.0
    assert row["median_income"] == 48000.0


def test_median_age_and_bands():
    counts = {age: 10 for age in range(0, 91)}
    assert t.aggregate_age_bands(counts)["age_0_15"] == 160
    assert t.median_age({30: 10, 40: 10}) == 30.0


# --- ArcGIS pagination -------------------------------------------------------


def test_fetch_arcgis_geojson_pages_by_returned_count():
    # The server caps each page at 2 even though we ask for more, and advances
    # by the offset we send. Paging must follow the actual returned count.
    rows = [{"id": i} for i in range(5)]

    def handler(request: httpx.Request) -> httpx.Response:
        from urllib.parse import parse_qs, urlparse

        q = parse_qs(urlparse(str(request.url)).query)
        offset = int(q["resultOffset"][0])
        return httpx.Response(200, json={"features": rows[offset : offset + 2]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fc = loaders.fetch_arcgis_geojson(
            "https://x/FeatureServer/0/query", page_size=1000, client=client
        )
    assert [f["id"] for f in fc["features"]] == [0, 1, 2, 3, 4]


def test_read_csv_handles_bom_and_semicolons():
    text = "﻿geography code;Total: All households;Owns outright\nE1;100;40\n"
    rows, code_field = loaders._read_csv(text)
    assert code_field == "geography code"
    assert rows[0]["geography code"] == "E1"
