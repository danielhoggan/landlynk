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


def test_fetch_csv_text_extracts_msoa_member_from_zip(tmp_path):
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("census2021-ts054-ltla.csv", "geography code,x\nE09,1\n")
        zf.writestr("census2021-ts054-msoa.csv", "geography code,x\nE02000001,2\n")
    zip_bytes = buf.getvalue()

    # Point _get_bytes at our in-memory zip via monkeypatching the module.
    import landlynk_worker.refdata.loaders as L

    orig = L._get_bytes
    L._get_bytes = lambda url: zip_bytes
    try:
        text = L._fetch_csv_text("https://x/census2021-ts054.zip", "MSOA")
    finally:
        L._get_bytes = orig
    assert "E02000001" in text
    assert "E09" not in text  # picked the MSOA member, not the LA one


def test_read_csv_handles_bom_and_semicolons():
    text = "﻿geography code;Total: All households;Owns outright\nE1;100;40\n"
    rows, code_field = loaders._read_csv(text)
    assert code_field == "geography code"
    assert rows[0]["geography code"] == "E1"


def test_house_price_rows_takes_most_recent_year():
    # HPSSA sheets run oldest to newest left to right; we must take the latest,
    # not the first match, or prices read decades out of date (the £46k bug).
    record = {
        "MSOA code": "E02005592",
        "MSOA name": "Norwich 009",
        "Year ending Dec 1995": "46000",
        "Year ending Dec 2010": "175000",
        "Year ending Sep 2023": "265000",
    }
    rows = loaders._house_price_rows([record], "MSOA")
    assert rows[0]["area_code"] == "E02005592"
    assert rows[0]["median_price"] == 265000.0


def test_house_price_rows_uses_explicit_median_column():
    record = {"MSOA code": "E1", "Median price": "300000"}
    rows = loaders._house_price_rows([record], "MSOA")
    assert rows[0]["median_price"] == 300000.0


def test_resolve_data_url_finds_ons_download_link():
    html = (
        b"<!DOCTYPE html><html><head></head><body>"
        b'<a href="/file?uri=/peoplepopulationandcommunity/housing/datasets/'
        b'medianhousepricesbymiddlelayersuperoutputarea/current/hpssa.xlsx" '
        b'class="download">Download xlsx</a></body></html>'
    )
    url = loaders._resolve_data_url(
        "https://www.ons.gov.uk/peoplepopulationandcommunity/housing/datasets/x",
        html,
    )
    assert url == (
        "https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/housing/"
        "datasets/medianhousepricesbymiddlelayersuperoutputarea/current/hpssa.xlsx"
    )


def test_resolve_data_url_none_for_real_file():
    # Real xlsx bytes start with the zip signature, not HTML.
    assert loaders._resolve_data_url("http://x/f.xlsx", b"PK\x03\x04rest") is None


def test_resolve_data_url_errors_on_page_without_link():
    import pytest

    with pytest.raises(ValueError):
        loaders._resolve_data_url(
            "http://x", b"<html><head></head><body>no file</body></html>"
        )


def test_green_space_rows_to_minutes_msoa_only():
    records = [
        {"MSOA code": "E02000001", "Average distance to nearest park (m)": "400"},
        {
            "MSOA code": "E01000001",
            "Average distance to nearest park (m)": "240",
        },  # LSOA, skip
        {"MSOA code": "W02000001", "Average distance to nearest park (m)": "800"},
    ]
    rows = loaders._green_space_rows(records, "MSOA")
    keyed = {r["area_code"]: r for r in rows}
    assert set(keyed) == {"E02000001", "W02000001"}
    assert keyed["E02000001"]["metric_key"] == "greenspace_minutes"
    assert keyed["E02000001"]["value"] == 5.0  # 400m / 80
    assert keyed["W02000001"]["value"] == 10.0


def test_imd_rows_aggregate_lsoa_to_msoa():
    lookup = [
        {"LSOA code": "E01000001", "MSOA code": "E02000001"},
        {"LSOA code": "E01000002", "MSOA code": "E02000001"},
    ]
    records = [
        {
            "LSOA code": "E01000001",
            "Index of Multiple Deprivation (IMD) Score": "20",
            "Decile": "3",
        },
        {
            "LSOA code": "E01000002",
            "Index of Multiple Deprivation (IMD) Score": "30",
            "Decile": "5",
        },
    ]
    rows = loaders._imd_rows(records, lookup, "MSOA")
    by_key = {r["metric_key"]: r for r in rows}
    assert by_key["imd_score"]["area_code"] == "E02000001"
    assert by_key["imd_score"]["value"] == 25.0  # mean(20,30)
    assert by_key["imd_decile"]["value"] == 4  # round(mean(3,5))


def test_school_points_converts_bng_and_flags_good():
    records = [
        {
            "EstablishmentStatus (name)": "Open",
            "Easting": "532000",
            "Northing": "181000",
            "OfstedRating (name)": "Outstanding",
        },
        {
            "EstablishmentStatus (name)": "Open",
            "Easting": "532100",
            "Northing": "181100",
            "OfstedRating (name)": "Requires improvement",
        },
        {
            "EstablishmentStatus (name)": "Closed",
            "Easting": "532200",
            "Northing": "181200",
            "OfstedRating (name)": "Good",
        },
        {
            "EstablishmentStatus (name)": "Open",
            "Easting": "0",
            "Northing": "0",
            "OfstedRating (name)": "Good",
        },
    ]
    pts = loaders._school_points(records)
    assert len(pts) == 2  # closed and zero-location dropped
    london = pts[0]
    assert -0.2 < london["lng"] < 0.1 and 51.4 < london["lat"] < 51.6  # ~London
    assert pts[0]["good"] is True and pts[1]["good"] is False


def test_crime_points_extracts_lat_long():
    records = [
        {"Longitude": "-1.5", "Latitude": "52.8", "Crime type": "Burglary"},
        {"Longitude": "", "Latitude": "", "Crime type": "No location"},
    ]
    pts = loaders._crime_points(records)
    assert pts == [(-1.5, 52.8)]
