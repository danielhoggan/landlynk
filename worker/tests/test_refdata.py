"""Server-side reference loading: transforms, ArcGIS paging and admin routing."""

from __future__ import annotations

import httpx
import pytest

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
    # Real ONS TS003 headers: the total reads 'Total' (not 'All households'), and
    # the single family aggregate sits alongside its sub-rows, which must not be
    # summed into it (that would double count).
    age = "geography code,Aged 10 years,Aged 20 years,Aged 90 years and over\nE1,100,200,:\n"
    hh = (
        "geography code,Household composition: Total; measures: Value,"
        "Household composition: One person household; measures: Value,"
        "Household composition: Single family household; measures: Value,"
        "Household composition: Single family household: Lone parent family; "
        "measures: Value,"
        "Household composition: Other household types; measures: Value\n"
        "E1,200,50,120,40,30\n"
    )
    rows = loaders._demographics_rows(age, hh, "MSOA")
    row = rows[0]
    assert row["age_0_15"] == 100
    assert row["age_16_34"] == 200
    assert row["age_75_plus"] is None  # the only 75+ value was suppressed
    assert row["households"] == 200
    # 120, the aggregate, not 160 (aggregate + the lone parent sub-row).
    assert row["family_household_share"] == 120 / 200


def test_demographics_load_rejects_unparseable_households(monkeypatch):
    # A household file whose columns do not match must fail loudly, not silently
    # null every household count.
    age = "geography code,Aged 10 years\nE1,100\n"
    bad_hh = "geography code,Mystery column\nE1,200\n"
    monkeypatch.setattr(
        loaders, "_fetch_csv_text", lambda url, area_type: age if url == "a" else bad_hh
    )
    monkeypatch.setattr(loaders, "_replace_table", lambda *a, **k: 1)
    with pytest.raises(ValueError, match="household-composition"):
        loaders.load_demographics(None, "a", "hh", "MSOA")


def test_demographics_load_accepts_real_ts003_format(monkeypatch):
    age = "geography code,Aged 10 years\nE1,100\n"
    hh = (
        "geography code,Household composition: Total; measures: Value,"
        "Household composition: Single family household; measures: Value\n"
        "E1,200,120\n"
    )
    monkeypatch.setattr(
        loaders, "_fetch_csv_text", lambda url, area_type: age if url == "a" else hh
    )
    captured: dict = {}
    monkeypatch.setattr(
        loaders,
        "_replace_table",
        lambda pool, table, cols, rows, **k: (captured.update(rows=rows), len(rows))[1],
    )
    loaders.load_demographics(None, "a", "hh", "MSOA")
    assert captured["rows"][0]["households"] == 200


def test_tenure_rows_to_shares():
    # Real ONS TS054 headers, with a 'Total' column and social-rented sub-rows
    # that must not inflate the aggregate.
    csv_text = (
        "geography code,Tenure of household: Total; measures: Value,"
        "Tenure of household: Owned: Owns outright; measures: Value,"
        "Tenure of household: Owned: Owns with a mortgage or loan; measures: Value,"
        "Tenure of household: Social rented; measures: Value,"
        "Tenure of household: Social rented: Rented from council; measures: Value,"
        "Tenure of household: Private rented; measures: Value\n"
        "E1,1000,250,400,150,90,200\n"
    )
    row = loaders._tenure_rows(csv_text, "MSOA")[0]
    assert row["owns_outright"] == 0.25
    assert row["owns_with_mortgage"] == 0.40
    assert row["social_rented"] == 0.15  # 150, not 240 (aggregate plus its sub-row)
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


def test_development_site_rows_from_brownfield_csv():
    # planning.data.gov.uk brownfield-land shape: a WKT point plus dwelling
    # capacity. Rows without a usable point are dropped.
    csv_text = (
        "reference,name,point,hectares,minimum-net-dwellings,maximum-net-dwellings\n"
        'BF1,Mill Road,POINT (-0.75 52.40),1.2,10,25\n'
        "BF2,No geometry,,0.5,5,8\n"
    )
    rows = loaders._development_site_rows(csv_text)
    assert len(rows) == 1
    site = rows[0]
    assert site["reference"] == "BF1"
    assert site["lat"] == 52.40 and site["lng"] == -0.75
    assert site["min_dwellings"] == 10 and site["max_dwellings"] == 25
    assert site["hectares"] == 1.2


def test_planit_filters_residential_inside_polygon():
    # PlanIt parser keeps residential applications inside the catchment polygon,
    # drops non-residential and those outside, with no network.
    from shapely.geometry import shape

    from landlynk_worker.pipeline.planit import _residential_sites_from_geojson

    poly = shape(
        {
            "type": "Polygon",
            "coordinates": [[[-1, 51], [-1, 52], [0, 52], [0, 51], [-1, 51]]],
        }
    )
    data = {
        "features": [
            {
                "geometry": {"type": "Point", "coordinates": [-0.5, 51.5]},
                "properties": {
                    "description": "Erection of 20 dwellings",
                    "address": "Mill Road",
                },
            },
            {
                "geometry": {"type": "Point", "coordinates": [-0.5, 51.5]},
                "properties": {
                    "description": "Single storey extension",
                    "address": "1 High St",
                },
            },
            {
                "geometry": {"type": "Point", "coordinates": [5, 51.5]},
                "properties": {"description": "50 homes", "address": "Far away"},
            },
            {
                "geometry": {"type": "Point", "coordinates": [-0.6, 51.6]},
                "properties": {
                    "app_size": "Large",
                    "description": "Mixed use",
                    "address": "Big site",
                },
            },
        ]
    }
    names = [s["name"] for s in _residential_sites_from_geojson(data, poly)]
    assert "Mill Road" in names  # residential keyword, inside
    assert "Big site" in names  # large application, inside
    assert "1 High St" not in names  # not residential
    assert "Far away" not in names  # outside the polygon


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


def test_green_space_rows_average_lsoa_to_msoa():
    # The ONS public green space tables are LSOA rows carrying an MSOA code; the
    # distance is meaned over the LSOAs in each MSOA, then converted to minutes.
    records = [
        {
            "MSOA code": "E02000001",
            "LSOA code": "E01000001",
            "Average distance to nearest Park, Public Garden or Playing Field (m)": "400",
        },
        {
            "MSOA code": "E02000001",
            "LSOA code": "E01000002",
            "Average distance to nearest Park, Public Garden or Playing Field (m)": "800",
        },
    ]
    rows = loaders._green_space_rows(records, "MSOA")
    assert len(rows) == 1
    assert rows[0]["area_code"] == "E02000001"
    assert rows[0]["value"] == 7.5  # mean(400, 800) / 80


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


def test_norm_postcode_uppercases_and_strips_spaces():
    assert loaders._norm_postcode("tf9 3rp") == "TF93RP"
    assert loaders._norm_postcode("  NN15  7FJ ") == "NN157FJ"
    assert loaders._norm_postcode("") == ""


def test_postcode_centroid_parses_and_drops_terminated():
    ok = loaders._postcode_centroid(
        {"pcds": "TF9 3RP", "lat": "52.91", "long": "-2.45"}
    )
    assert ok == ("TF93RP", 52.91, -2.45)
    # Terminated postcode without a grid reference (sentinel latitude) is dropped.
    assert (
        loaders._postcode_centroid(
            {"pcds": "AB1 0AA", "lat": "99.999999", "long": "0.0"}
        )
        is None
    )
    assert loaders._postcode_centroid({"pcds": "", "lat": "1", "long": "1"}) is None


def test_is_ods_url():
    assert loaders._is_ods_url(
        "https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations"
    )
    assert not loaders._is_ods_url("https://www.example.com/hospitals.csv")


def test_hospital_points_latlng_and_bng():
    records = [
        {
            "OrganisationName": "City Hospital",
            "ParentODSCode": "RXX",
            "Latitude": "52.5",
            "Longitude": "-1.9",
        },
        {
            "OrganisationName": "No location",
            "ParentODSCode": "RYY",
            "Latitude": "",
            "Longitude": "",
        },
    ]
    pts = loaders._hospital_points(records)
    assert len(pts) == 1
    assert pts[0]["org_code"] == "RXX" and pts[0]["lat"] == 52.5


def test_load_records_dated_steps_back_to_available_day(monkeypatch):
    # Today's GIAS file is not up yet; yesterday's is. The loader steps back.
    available = "20260610"
    seen = []

    def fake_get_bytes(u):
        seen.append(u)
        if available in u:
            return b"URN,Easting,Northing,OfstedRating (name)\n1,532000,181000,Good\n"
        raise RuntimeError("404")

    monkeypatch.setattr(loaders, "_get_bytes", fake_get_bytes)
    url = "https://gias/edubasealldata20260612.csv"
    records = loaders._load_records_dated(url, max_back=5)
    assert records and records[0]["URN"] == "1"
    assert any("20260612" in u for u in seen) and any(available in u for u in seen)


def test_load_records_dated_errors_after_window(monkeypatch):
    import pytest

    monkeypatch.setattr(
        loaders, "_get_bytes", lambda u: (_ for _ in ()).throw(RuntimeError("404"))
    )
    with pytest.raises(ValueError):
        loaders._load_records_dated(
            "https://gias/edubasealldata20260612.csv", max_back=3
        )
