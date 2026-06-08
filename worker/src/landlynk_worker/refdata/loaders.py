"""Server-side reference data loaders.

The worker downloads ONS/OS open data over HTTP and loads it straight into
PostGIS, so reference data is loaded from the deployed app with no local
commands. Boundaries come from the ONS Open Geography Portal ArcGIS service
(paginated GeoJSON); census and income come from CSV or XLSX URLs.

Each load replaces its target table and records provenance in reference_load in
one transaction, so a refresh is atomic and auditable.
"""

from __future__ import annotations

import csv
import io
import json
from typing import TYPE_CHECKING
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx

from . import transforms as t

if TYPE_CHECKING:
    from psycopg_pool import ConnectionPool

_TIMEOUT = httpx.Timeout(120.0)


# --- HTTP download -----------------------------------------------------------


def _get_text(url: str) -> str:
    with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text


def _get_bytes(url: str) -> bytes:
    with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.content


def fetch_arcgis_geojson(
    query_url: str,
    out_fields: str = "*",
    page_size: int = 2000,
    client: httpx.Client | None = None,
) -> dict:
    """Page an ArcGIS FeatureServer query endpoint into one GeoJSON FeatureCollection.

    ``query_url`` is the layer's .../query URL (from the ONS portal API). Our
    parameters are merged over any already present so a pasted URL still works.
    The client is injectable for testing.
    """
    parts = urlparse(query_url)
    base_params = dict(parse_qsl(parts.query))
    owned = client is None
    client = client or httpx.Client(timeout=_TIMEOUT, follow_redirects=True)
    features: list[dict] = []
    offset = 0
    try:
        while True:
            params = {
                **base_params,
                "where": base_params.get("where", "1=1"),
                "outFields": out_fields,
                "outSR": "4326",
                "f": "geojson",
                "resultOffset": str(offset),
                "resultRecordCount": str(page_size),
            }
            url = urlunparse(parts._replace(query=urlencode(params)))
            resp = client.get(url)
            resp.raise_for_status()
            batch = resp.json().get("features") or []
            features.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size
    finally:
        if owned:
            client.close()
    return {"type": "FeatureCollection", "features": features}


def _read_csv(text: str) -> tuple[list[dict], str]:
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    code_field = t.find_area_code_field(reader.fieldnames or [])
    return rows, code_field


def _read_xlsx(content: bytes) -> list[dict]:
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    header = [str(c) if c is not None else "" for c in next(rows_iter)]
    return [dict(zip(header, values, strict=False)) for values in rows_iter]


# --- Transforms to rows ------------------------------------------------------

_BOUNDARY_KEYS = {
    "MSOA": {"code": "MSOA21CD", "name": "MSOA21NM"},
    "LA": {"code": "LAD21CD", "name": "LAD21NM"},
}


def _boundary_rows(geojson: dict, area_type: str) -> list[dict]:
    keys = _BOUNDARY_KEYS[area_type]
    rows: list[dict] = []
    for feature in geojson.get("features") or []:
        props = feature.get("properties") or {}
        geometry = feature.get("geometry")
        code = str(props.get(keys["code"]) or "").strip()
        if not code or geometry is None:
            continue
        rows.append(
            {
                "area_code": code,
                "area_type": area_type,
                "area_name": str(props.get(keys["name"]) or "").strip() or None,
                "geom": json.dumps(geometry),
            }
        )
    return rows


def _demographics_rows(
    age_text: str, households_text: str, area_type: str
) -> list[dict]:
    age_rows, age_code = _read_csv(age_text)
    hh_rows, hh_code = _read_csv(households_text)

    households_by_area: dict[str, tuple[int | None, float | None]] = {}
    for record in hh_rows:
        code = (record.get(hh_code) or "").strip()
        if not code:
            continue
        total = t.sum_matching(record, hh_code, ("all households",))
        family = t.sum_matching(record, hh_code, ("single family", "one family"))
        households_by_area[code] = (total, t.share(family, total))

    rows: list[dict] = []
    for record in age_rows:
        code = (record.get(age_code) or "").strip()
        if not code:
            continue
        counts = t.single_year_counts(record, age_code)
        bands = t.aggregate_age_bands(counts)
        population = sum(v for v in counts.values() if v is not None) or None
        households, family_share = households_by_area.get(code, (None, None))
        rows.append(
            {
                "area_code": code,
                "area_type": area_type,
                "population": population,
                "households": households,
                **bands,
                "median_age": t.median_age(counts),
                "family_household_share": family_share,
            }
        )
    return rows


def _tenure_rows(text: str, area_type: str) -> list[dict]:
    records, code_field = _read_csv(text)
    rows: list[dict] = []
    for record in records:
        code = (record.get(code_field) or "").strip()
        if not code:
            continue
        total = t.sum_matching(record, code_field, ("all households",))
        rows.append(
            {
                "area_code": code,
                "area_type": area_type,
                "owns_outright": t.share(
                    t.sum_matching(record, code_field, ("owns outright",)), total
                ),
                "owns_with_mortgage": t.share(
                    t.sum_matching(
                        record, code_field, ("mortgage", "shared ownership")
                    ),
                    total,
                ),
                "social_rented": t.share(
                    t.sum_matching(record, code_field, ("social rented",)), total
                ),
                "private_rented": t.share(
                    t.sum_matching(record, code_field, ("private rented", "rent free")),
                    total,
                ),
            }
        )
    return rows


def _income_rows(records: list[dict], area_type: str) -> list[dict]:
    if not records:
        return []
    fieldnames = list(records[0].keys())
    code_col = t.find_column(
        fieldnames, ("msoa code", "area code", "geography code", "code")
    )
    mean_col = t.find_column(fieldnames, ("net annual income (mean)", "mean"))
    median_col = t.find_column(fieldnames, ("net annual income (median)", "median"))
    if code_col is None:
        raise ValueError(f"No area code column found in {fieldnames}")
    rows: list[dict] = []
    for record in records:
        code = str(record.get(code_col) or "").strip()
        if not code:
            continue
        rows.append(
            {
                "area_code": code,
                "area_type": area_type,
                "median_income": (
                    t.parse_number(record.get(median_col)) if median_col else None
                ),
                "mean_income": (
                    t.parse_number(record.get(mean_col)) if mean_col else None
                ),
            }
        )
    return rows


# --- DB write ----------------------------------------------------------------


def _replace_table(
    pool: ConnectionPool,
    table: str,
    columns: tuple[str, ...],
    rows: list[dict],
    source: str,
    geometry_columns: dict[str, str] | None = None,
) -> int:
    geometry_columns = geometry_columns or {}
    col_list = ", ".join(columns)
    placeholders = ", ".join(geometry_columns.get(c, "%s") for c in columns)
    insert_sql = f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})"
    with pool.connection() as conn, conn.transaction():
        conn.execute(f"TRUNCATE {table}")
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(insert_sql, [row.get(c) for c in columns])
        conn.execute(
            "INSERT INTO reference_load (table_name, source, source_version) "
            "VALUES (%s, %s, %s)",
            [table, source, "downloaded"],
        )
    return len(rows)


# --- Public load functions ---------------------------------------------------


def load_boundaries(pool: ConnectionPool, url: str, area_type: str = "MSOA") -> int:
    keys = _BOUNDARY_KEYS[area_type]
    geojson = fetch_arcgis_geojson(url, out_fields=f"{keys['code']},{keys['name']}")
    rows = _boundary_rows(geojson, area_type)
    return _replace_table(
        pool,
        "geo_boundaries",
        ("area_code", "area_type", "area_name", "geom"),
        rows,
        source="ONS Open Geography Portal",
        geometry_columns={"geom": "ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326))"},
    )


def load_demographics(
    pool: ConnectionPool, age_url: str, households_url: str, area_type: str = "MSOA"
) -> int:
    rows = _demographics_rows(_get_text(age_url), _get_text(households_url), area_type)
    return _replace_table(
        pool,
        "census_demographics",
        (
            "area_code",
            "area_type",
            "population",
            "households",
            "age_0_15",
            "age_16_34",
            "age_35_54",
            "age_55_74",
            "age_75_plus",
            "median_age",
            "family_household_share",
        ),
        rows,
        source="ONS Census 2021",
    )


def load_tenure(pool: ConnectionPool, url: str, area_type: str = "MSOA") -> int:
    rows = _tenure_rows(_get_text(url), area_type)
    return _replace_table(
        pool,
        "census_tenure",
        (
            "area_code",
            "area_type",
            "owns_outright",
            "owns_with_mortgage",
            "social_rented",
            "private_rented",
        ),
        rows,
        source="ONS Census 2021",
    )


def load_income(pool: ConnectionPool, url: str, area_type: str = "MSOA") -> int:
    if url.lower().endswith((".xlsx", ".xlsm")):
        records = _read_xlsx(_get_bytes(url))
    else:
        records, _ = _read_csv(_get_text(url))
    rows = _income_rows(records, area_type)
    return _replace_table(
        pool,
        "income_estimates",
        ("area_code", "area_type", "median_income", "mean_income"),
        rows,
        source="ONS income estimates",
    )
