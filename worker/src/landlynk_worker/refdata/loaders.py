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
import zipfile
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
    # Advance by the number actually returned, not the requested page size:
    # ArcGIS servers commonly cap a page below the requested count, which would
    # otherwise skip records. Stop when a page comes back empty.
    try:
        for _ in range(10_000):  # safety bound against a server ignoring offset
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
            if not batch:
                break
            features.extend(batch)
            offset += len(batch)
    finally:
        if owned:
            client.close()
    return {"type": "FeatureCollection", "features": features}


def _read_csv(text: str) -> tuple[list[dict], str]:
    # Strip a UTF-8 BOM so the first header is not "﻿geography code".
    if text.startswith("﻿"):
        text = text[1:]
    # Sniff the delimiter (NOMIS uses commas, some ONS exports use semicolons or
    # tabs); fall back to comma.
    try:
        delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t").delimiter
    except csv.Error:
        delimiter = ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    rows = list(reader)
    code_field = t.find_area_code_field(reader.fieldnames or [])
    return rows, code_field


# Keyword to find the right geography CSV inside a NOMIS bulk zip.
_AREA_TYPE_KEYWORD = {"MSOA": "msoa", "LA": "ltla"}


def _fetch_csv_text(url: str, area_type: str) -> str:
    """Return CSV text from a URL, transparently handling a NOMIS bulk .zip.

    NOMIS bulk census downloads are zips containing one CSV per geography
    (e.g. census2021-ts054-msoa.csv). We pick the member matching the area type
    so census loads are a one-click download.
    """
    if not url.lower().endswith(".zip"):
        return _get_text(url)
    content = _get_bytes(url)
    keyword = _AREA_TYPE_KEYWORD.get(area_type, "msoa")
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        csv_names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        match = next((n for n in csv_names if keyword in n.lower()), None)
        if match is None and area_type == "LA":
            # Fall back to other LA spellings used across releases.
            match = next(
                (n for n in csv_names if any(k in n.lower() for k in ("lad", "utla"))),
                None,
            )
        if match is None and csv_names:
            match = csv_names[0]
        if match is None:
            raise ValueError(f"No CSV found in zip at {url}")
        return zf.read(match).decode("utf-8-sig")


_XLSX_CODE_HINTS = (
    "msoa code",
    "area code",
    "geography code",
    "msoa11cd",
    "msoa21cd",
    "lad code",
    "la code",
)


def _looks_like_header(cells: list[str]) -> bool:
    """True if a row looks like the data header (carries an area-code column).

    ONS spreadsheets have title and notes rows before the real header, so we
    scan for the first row that has an area-code column and several fields.
    """
    low = [c.lower() for c in cells]
    has_code = any(c in _XLSX_CODE_HINTS for c in low) or any(
        "msoa" in c and "code" in c for c in low
    )
    return has_code and sum(1 for c in cells if c) >= 3


def _read_xlsx(content: bytes) -> list[dict]:
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    for ws in wb.worksheets:
        rows = list(ws.iter_rows(values_only=True))
        for i, row in enumerate(rows[:40]):
            cells = [str(c).strip() if c is not None else "" for c in row]
            if _looks_like_header(cells):
                records = [dict(zip(cells, r, strict=False)) for r in rows[i + 1 :]]
                records = [r for r in records if any(v is not None for v in r.values())]
                if records:
                    return records
    # Fallback: first sheet, header in row 1.
    ws = wb.active
    it = ws.iter_rows(values_only=True)
    header = [str(c) if c is not None else "" for c in next(it)]
    return [dict(zip(header, v, strict=False)) for v in it]


def _read_xls(content: bytes) -> list[dict]:
    """Read a legacy .xls workbook (e.g. ONS HPSSA) into records.

    Mirrors _read_xlsx: find the header row by its shape, then map rows to dicts.
    """
    import xlrd

    wb = xlrd.open_workbook(file_contents=content)
    for sheet in wb.sheets():
        rows = [
            [sheet.cell_value(r, c) for c in range(sheet.ncols)]
            for r in range(sheet.nrows)
        ]
        for i, row in enumerate(rows[:40]):
            cells = [str(c).strip() if c is not None else "" for c in row]
            if _looks_like_header(cells):
                records = [dict(zip(cells, r, strict=False)) for r in rows[i + 1 :]]
                records = [r for r in records if any(v != "" for v in r.values())]
                if records:
                    return records
    sheet = wb.sheet_by_index(0)
    header = [str(sheet.cell_value(0, c)) for c in range(sheet.ncols)]
    return [
        dict(
            zip(
                header,
                [sheet.cell_value(r, c) for c in range(sheet.ncols)],
                strict=False,
            )
        )
        for r in range(1, sheet.nrows)
    ]


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
    # ONS small-area income is mean-based ("Net annual income (£)"); match it
    # broadly. Median is often absent at MSOA level.
    mean_col = t.find_column(
        fieldnames,
        (
            "net annual income (mean)",
            "net annual income",
            "mean income",
            "mean",
            "income",
        ),
    )
    median_col = t.find_column(
        fieldnames, ("net annual income (median)", "median income", "median")
    )
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


def _house_price_rows(records: list[dict], area_type: str) -> list[dict]:
    """ONS HPSSA median price paid by area. The price is the last year column.

    HPSSA sheets carry a column per period; we take the rightmost numeric value
    column (the most recent) after detecting the area code column.
    """
    if not records:
        return []
    fieldnames = list(records[0].keys())
    code_col = t.find_column(
        fieldnames, ("msoa code", "area code", "geography code", "code")
    )
    if code_col is None:
        raise ValueError(f"No area code column found in {fieldnames}")
    # Prefer an explicit median price column; else the last column with a year.
    price_col = t.find_column(fieldnames, ("year ending", "median price", "price"))
    if price_col is None:
        year_cols = [f for f in fieldnames if any(c.isdigit() for c in str(f))]
        price_col = year_cols[-1] if year_cols else None
    rows: list[dict] = []
    for record in records:
        code = str(record.get(code_col) or "").strip()
        if not code:
            continue
        rows.append(
            {
                "area_code": code,
                "area_type": area_type,
                "median_price": (
                    t.parse_number(record.get(price_col)) if price_col else None
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
    params = [[row.get(c) for c in columns] for row in rows]
    with pool.connection() as conn, conn.transaction():
        conn.execute(f"TRUNCATE {table}")
        with conn.cursor() as cur:
            # Batched insert: far faster than per-row for thousands of areas.
            cur.executemany(insert_sql, params)
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
    rows = _demographics_rows(
        _fetch_csv_text(age_url, area_type),
        _fetch_csv_text(households_url, area_type),
        area_type,
    )
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
    rows = _tenure_rows(_fetch_csv_text(url, area_type), area_type)
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


def load_house_prices(pool: ConnectionPool, url: str, area_type: str = "MSOA") -> int:
    low = url.lower()
    if low.endswith(".xls"):
        records = _read_xls(_get_bytes(url))
    elif low.endswith((".xlsx", ".xlsm")):
        records = _read_xlsx(_get_bytes(url))
    else:
        records, _ = _read_csv(_get_text(url))
    rows = _house_price_rows(records, area_type)
    return _replace_table(
        pool,
        "house_prices",
        ("area_code", "area_type", "median_price"),
        rows,
        source="ONS HPSSA",
    )
