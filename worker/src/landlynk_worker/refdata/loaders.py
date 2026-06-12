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
import re
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


# ONS dataset pages link to the actual file as /file?uri=...xlsx (or xls/csv).
_ONS_FILE_RE = re.compile(
    r'href="(/file\?uri=[^"]+\.(?:xlsx|xlsm|xls|csv))"', re.IGNORECASE
)


def _resolve_data_url(url: str, data: bytes) -> str | None:
    """If `data` is an HTML page (e.g. an ONS dataset page was pasted instead of
    the file), find the first xlsx/xls/csv download link and return its absolute
    URL. Returns None when the content is already a data file."""
    head = data[:1024].lstrip().lower()
    if not (
        head.startswith(b"<!doctype html")
        or head.startswith(b"<html")
        or b"<head" in head
    ):
        return None
    from urllib.parse import urljoin

    match = _ONS_FILE_RE.search(data.decode("utf-8", "ignore"))
    if not match:
        raise ValueError(
            "That URL is a web page, not a data file. Open the dataset page, then "
            "copy the link of the xlsx or csv download itself and paste that."
        )
    return urljoin(url, match.group(1))


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


def _csv_rows(text: str) -> list[dict]:
    """Parse CSV text into dict rows, handling a BOM and the delimiter. Does not
    require an area-code column, so point files (schools, hospitals) parse too."""
    if text.startswith("﻿"):
        text = text[1:]
    try:
        delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t").delimiter
    except csv.Error:
        delimiter = ","
    return list(csv.DictReader(io.StringIO(text), delimiter=delimiter))


def _read_csv(text: str) -> tuple[list[dict], str]:
    rows = _csv_rows(text)
    fieldnames = list(rows[0].keys()) if rows else []
    code_field = t.find_area_code_field(fieldnames)
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
    """ONS HPSSA median price paid by area, taking the most recent period.

    HPSSA sheets carry one column per rolling year, running chronologically from
    1995 (e.g. "Year ending Dec 1995" ... "Year ending Sep 2023"). We must take
    the most recent (rightmost dated) column, not the first match, or prices read
    decades out of date.
    """
    if not records:
        return []
    fieldnames = list(records[0].keys())
    code_col = t.find_column(
        fieldnames, ("msoa code", "area code", "geography code", "code")
    )
    if code_col is None:
        raise ValueError(f"No area code column found in {fieldnames}")
    # A single explicit median price column (some CSV variants), else the latest
    # dated period column. Dated columns are ordered oldest to newest left to
    # right, so the last one holding a 19xx/20xx year is the most recent price.
    price_col = t.find_column(fieldnames, ("median price", "median_price"))
    if price_col is None:
        dated = [f for f in fieldnames if re.search(r"(?:19|20)\d{2}", str(f))]
        price_col = dated[-1] if dated else t.find_column(fieldnames, ("price",))
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


def _records_from_bytes(url: str, data: bytes) -> list[dict]:
    """Parse already-downloaded bytes, following an ONS page link if pasted."""
    resolved = _resolve_data_url(url, data)
    if resolved:
        url = resolved
        data = _get_bytes(url)
    low = url.lower()
    if low.endswith(".xls"):
        return _read_xls(data)
    if low.endswith((".xlsx", ".xlsm")):
        return _read_xlsx(data)
    return _csv_rows(data.decode("utf-8-sig", "ignore"))


def _load_records(url: str) -> list[dict]:
    """Fetch a tabular file (xlsx/xls/csv), following an ONS page link if pasted."""
    return _records_from_bytes(url, _get_bytes(url))


def _load_records_dated(url: str, max_back: int = 10) -> list[dict]:
    """Load a date-stamped file (e.g. GIAS edubasealldataYYYYMMDD.csv).

    Files like GIAS are published daily with the date in the name, so there is no
    fixed link. Given a URL containing a YYYYMMDD, try that date then step back a
    day at a time until one downloads, so a default of today's date just works
    even before the day's file is published. Falls back to a clear error asking
    for a manual URL if none in the window exist.
    """
    from datetime import datetime, timedelta

    match = re.search(r"\d{8}", url)
    if not match:
        return _load_records(url)
    stamp = match.group(0)
    try:
        base = datetime.strptime(stamp, "%Y%m%d").date()
    except ValueError:
        return _load_records(url)
    last_error: Exception | None = None
    for i in range(max_back):
        day = (base - timedelta(days=i)).strftime("%Y%m%d")
        candidate = url.replace(stamp, day, 1)
        try:
            return _records_from_bytes(candidate, _get_bytes(candidate))
        except Exception as exc:  # download miss for that day; try the day before
            last_error = exc
    raise ValueError(
        "Could not find a published file in the last "
        f"{max_back} days from {url}. Paste a specific file URL instead. "
        f"Last error: {last_error}"
    )


def _is_msoa(code: str) -> bool:
    return code[:3] in ("E02", "W02")


def _green_space_rows(records: list[dict], area_type: str) -> list[dict]:
    """ONS access to green space, as minutes walk to the nearest green space.

    Distance (metres) to the nearest publicly accessible green space is converted
    to a walk time at ~80 m/min. Keeps MSOA rows only, so the file can carry
    several geography levels.
    """
    if not records:
        return []
    fields = list(records[0].keys())
    code_col = t.find_column(
        fields, ("msoa code", "msoa11cd", "msoa21cd", "area code", "geography code")
    )
    dist_col = t.find_column(
        fields,
        (
            "average distance to nearest park",
            "average distance to nearest publicly",
            "distance to nearest",
            "average distance",
        ),
    )
    if code_col is None or dist_col is None:
        raise ValueError(f"No MSOA code / distance column found in {fields}")
    rows: list[dict] = []
    for r in records:
        code = str(r.get(code_col) or "").strip()
        if not _is_msoa(code):
            continue
        metres = t.parse_number(r.get(dist_col))
        if metres is None:
            continue
        rows.append(
            {
                "area_code": code,
                "area_type": area_type,
                "metric_key": "greenspace_minutes",
                "value": round(metres / 80.0, 1),
            }
        )
    return rows


def _imd_rows(records: list[dict], lookup: list[dict], area_type: str) -> list[dict]:
    """Index of Multiple Deprivation, aggregated from LSOA to MSOA.

    IMD is published at LSOA, so we map LSOA to MSOA with the supplied lookup and
    take the mean score and mean decile per MSOA (an indicative area summary).
    """
    if not records or not lookup:
        return []
    lf = list(lookup[0].keys())
    lsoa_l = t.find_column(lf, ("lsoa code", "lsoa11cd", "lsoa21cd", "lsoa"))
    msoa_l = t.find_column(lf, ("msoa code", "msoa11cd", "msoa21cd", "msoa"))
    if lsoa_l is None or msoa_l is None:
        raise ValueError(f"Lookup needs LSOA and MSOA code columns, got {lf}")
    to_msoa = {
        str(r.get(lsoa_l) or "").strip(): str(r.get(msoa_l) or "").strip()
        for r in lookup
    }

    rf = list(records[0].keys())
    lsoa_c = t.find_column(rf, ("lsoa code", "lsoa11cd", "lsoa21cd", "lsoa"))
    score_c = t.find_column(
        rf,
        (
            "index of multiple deprivation (imd) score",
            "index of multiple deprivation score",
            "imd score",
        ),
    )
    decile_c = t.find_column(rf, ("decile",))
    if lsoa_c is None or (score_c is None and decile_c is None):
        raise ValueError(f"No LSOA code / IMD score column found in {rf}")

    scores: dict[str, list[float]] = {}
    deciles: dict[str, list[float]] = {}
    for r in records:
        msoa = to_msoa.get(str(r.get(lsoa_c) or "").strip())
        if not _is_msoa(msoa or ""):
            continue
        if score_c:
            s = t.parse_number(r.get(score_c))
            if s is not None:
                scores.setdefault(msoa, []).append(s)
        if decile_c:
            d = t.parse_number(r.get(decile_c))
            if d is not None:
                deciles.setdefault(msoa, []).append(d)

    rows: list[dict] = []
    for msoa in set(scores) | set(deciles):
        if scores.get(msoa):
            rows.append(_metric_row(msoa, area_type, "imd_score", _mean(scores[msoa])))
        if deciles.get(msoa):
            rows.append(
                _metric_row(msoa, area_type, "imd_decile", round(_mean(deciles[msoa])))
            )
    return rows


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _metric_row(code: str, area_type: str, key: str, value: float) -> dict:
    return {
        "area_code": code,
        "area_type": area_type,
        "metric_key": key,
        "value": value,
    }


def _replace_metric(
    pool: ConnectionPool, metric_keys: list[str], rows: list[dict]
) -> int:
    """Replace all rows for the given metric_keys with the supplied rows."""
    with pool.connection() as conn, conn.transaction():
        conn.execute(
            "DELETE FROM area_metric WHERE metric_key = ANY(%s)", [list(metric_keys)]
        )
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO area_metric (area_code, area_type, metric_key, value) "
                "VALUES (%s, %s, %s, %s)",
                [
                    (r["area_code"], r["area_type"], r["metric_key"], r["value"])
                    for r in rows
                ],
            )
    return len(rows)


def load_green_space(pool: ConnectionPool, url: str, area_type: str = "MSOA") -> int:
    rows = _green_space_rows(_load_records(url), area_type)
    return _replace_metric(pool, ["greenspace_minutes"], rows)


def load_imd(
    pool: ConnectionPool, url: str, lookup_url: str, area_type: str = "MSOA"
) -> int:
    rows = _imd_rows(_load_records(url), _load_records(lookup_url), area_type)
    return _replace_metric(pool, ["imd_score", "imd_decile"], rows)


# --- point datasets (schools, crime): point-in-MSOA via PostGIS ---------------


def _bng_to_wgs(easting: float, northing: float) -> tuple[float, float]:
    from pyproj import Transformer

    global _BNG
    try:
        tr = _BNG
    except NameError:
        tr = _BNG = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
    lng, lat = tr.transform(easting, northing)
    return lng, lat


_GOOD_RATINGS = {"outstanding", "good"}


def _school_points(records: list[dict]) -> list[dict]:
    """Open schools as {lng, lat, good} from a GIAS extract (easting/northing).

    GIAS carries both the location and the Ofsted rating, so one file suffices.
    Only open schools with a location and a rating are kept.
    """
    if not records:
        return []
    f = list(records[0].keys())
    east_c = t.find_column(f, ("easting",))
    north_c = t.find_column(f, ("northing",))
    rating_c = t.find_column(
        f, ("ofstedrating (name)", "ofsted rating", "ofstedrating")
    )
    status_c = t.find_column(f, ("establishmentstatus (name)", "establishmentstatus"))
    if east_c is None or north_c is None or rating_c is None:
        raise ValueError(f"GIAS needs easting, northing and Ofsted rating, got {f}")
    points: list[dict] = []
    for r in records:
        if status_c and not str(r.get(status_c) or "").strip().lower().startswith(
            "open"
        ):
            continue
        rating = str(r.get(rating_c) or "").strip().lower()
        if not rating or rating in ("not applicable", "", "none"):
            continue
        easting = t.parse_number(r.get(east_c))
        northing = t.parse_number(r.get(north_c))
        if easting is None or northing is None or easting == 0:
            continue
        lng, lat = _bng_to_wgs(easting, northing)
        points.append({"lng": lng, "lat": lat, "good": rating in _GOOD_RATINGS})
    return points


def _crime_points(records: list[dict]) -> list[tuple[float, float]]:
    """Crime incidents as (lng, lat) from data.police.uk street-level CSV rows."""
    if not records:
        return []
    f = list(records[0].keys())
    lng_c = t.find_column(f, ("longitude", "long", "lng"))
    lat_c = t.find_column(f, ("latitude", "lat"))
    if lng_c is None or lat_c is None:
        raise ValueError(f"Crime CSV needs longitude and latitude, got {f}")
    out: list[tuple[float, float]] = []
    for r in records:
        lng = t.parse_number(r.get(lng_c))
        lat = t.parse_number(r.get(lat_c))
        if lng is not None and lat is not None:
            out.append((lng, lat))
    return out


def _read_point_records(url: str) -> list[dict]:
    """Records from a CSV/XLSX, or every CSV inside a zip (data.police.uk archive)."""
    if not url.lower().endswith(".zip"):
        return _load_records(url)
    content = _get_bytes(url)
    rows: list[dict] = []
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        for name in zf.namelist():
            if name.lower().endswith(".csv"):
                rows.extend(_csv_rows(zf.read(name).decode("utf-8-sig", "ignore")))
    return rows


def load_schools(
    pool: ConnectionPool, url: str, area_type: str = "MSOA"
) -> int:  # pragma: no cover - PostGIS spatial join, exercised live
    points = _school_points(_load_records_dated(url))
    if not points:
        return 0
    with pool.connection() as conn, conn.transaction():
        conn.execute(
            "CREATE TEMP TABLE _sch (lng float8, lat float8, good bool) "
            "ON COMMIT DROP"
        )
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO _sch VALUES (%s, %s, %s)",
                [(p["lng"], p["lat"], p["good"]) for p in points],
            )
        conn.execute(
            "DELETE FROM area_metric WHERE metric_key IN "
            "('schools_count', 'schools_good_pct')"
        )
        conn.execute(
            "INSERT INTO area_metric (area_code, area_type, metric_key, value) "
            "SELECT b.area_code, %s, 'schools_count', count(*) "
            "FROM _sch s JOIN geo_boundaries b "
            "ON b.area_type = %s AND ST_Contains("
            "b.geom, ST_SetSRID(ST_MakePoint(s.lng, s.lat), 4326)) "
            "GROUP BY b.area_code",
            [area_type, area_type],
        )
        conn.execute(
            "INSERT INTO area_metric (area_code, area_type, metric_key, value) "
            "SELECT b.area_code, %s, 'schools_good_pct', "
            "round(100.0 * count(*) FILTER (WHERE s.good) / NULLIF(count(*), 0)) "
            "FROM _sch s JOIN geo_boundaries b "
            "ON b.area_type = %s AND ST_Contains("
            "b.geom, ST_SetSRID(ST_MakePoint(s.lng, s.lat), 4326)) "
            "GROUP BY b.area_code",
            [area_type, area_type],
        )
        n = conn.execute(
            "SELECT count(*) FROM area_metric WHERE metric_key = 'schools_count'"
        ).fetchone()[0]
    return int(n)


def _hospital_points(records: list[dict]) -> list[dict]:
    """Hospitals as {name, org_code, lng, lat} from an NHS sites file.

    Accepts lat/long columns directly, or easting/northing (BNG) which we
    reproject. Org code (parent/trust ODS code) is kept for the waiting-times
    join when present.
    """
    if not records:
        return []
    f = list(records[0].keys())
    lat_c = t.find_column(f, ("latitude", "lat"))
    lng_c = t.find_column(f, ("longitude", "long", "lng"))
    east_c = t.find_column(f, ("easting",))
    north_c = t.find_column(f, ("northing",))
    name_c = t.find_column(
        f, ("organisationname", "hospital name", "name", "site name")
    )
    org_c = t.find_column(
        f,
        (
            "parentodscode",
            "parent organisation code",
            "trust code",
            "organisationcode",
            "org code",
        ),
    )
    points: list[dict] = []
    for r in records:
        lat = lng = None
        if lat_c and lng_c:
            lat = t.parse_number(r.get(lat_c))
            lng = t.parse_number(r.get(lng_c))
        elif east_c and north_c:
            e = t.parse_number(r.get(east_c))
            n = t.parse_number(r.get(north_c))
            if e and n:
                lng, lat = _bng_to_wgs(e, n)
        if lat is None or lng is None or (lat == 0 and lng == 0):
            continue
        points.append(
            {
                "name": str(r.get(name_c) or "").strip() if name_c else None,
                "org_code": str(r.get(org_c) or "").strip() if org_c else None,
                "lat": lat,
                "lng": lng,
            }
        )
    return points


def load_hospitals(
    pool: ConnectionPool, url: str, area_type: str = "MSOA"
) -> int:  # pragma: no cover - PostGIS spatial join, exercised live
    points = _hospital_points(_load_records(url))
    if not points:
        return 0
    with pool.connection() as conn, conn.transaction():
        conn.execute("TRUNCATE hospital")
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO hospital (name, org_code, lat, lng, geom) "
                "VALUES (%s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))",
                [
                    (p["name"], p["org_code"], p["lat"], p["lng"], p["lng"], p["lat"])
                    for p in points
                ],
            )
        # Per-MSOA distance to the nearest hospital, in km (great-circle).
        conn.execute("DELETE FROM area_metric WHERE metric_key = 'hospital_km'")
        conn.execute(
            "INSERT INTO area_metric (area_code, area_type, metric_key, value) "
            "SELECT b.area_code, %s, 'hospital_km', round((("
            "  SELECT ST_Distance(ST_Centroid(b.geom)::geography, h.geom::geography) "
            "  FROM hospital h ORDER BY ST_Centroid(b.geom) <-> h.geom LIMIT 1"
            ") / 1000.0)::numeric, 1) "
            "FROM geo_boundaries b WHERE b.area_type = %s",
            [area_type, area_type],
        )
    return len(points)


def _nhs_waiting_rows(records: list[dict]) -> list[dict]:
    """Per-provider NHS waiting metrics from an A&E/RTT CSV.

    Flexible to the published column names: an organisation code, optional name,
    a four-hour A&E performance percentage and an RTT median wait in weeks.
    """
    if not records:
        return []
    f = list(records[0].keys())
    org_c = t.find_column(
        f, ("org code", "organisation code", "provider org code", "code")
    )
    name_c = t.find_column(
        f, ("org name", "organisation name", "provider name", "name")
    )
    ae_c = t.find_column(
        f,
        (
            "percentage in 4 hours or less (all)",
            "4 hours or less",
            "four hour performance",
            "a&e 4 hours",
        ),
    )
    rtt_c = t.find_column(
        f, ("median (weeks)", "median wait (weeks)", "rtt median", "median weeks")
    )
    if org_c is None or (ae_c is None and rtt_c is None):
        raise ValueError(f"NHS waiting file needs an org code and a metric, got {f}")
    rows: list[dict] = []
    for r in records:
        code = str(r.get(org_c) or "").strip()
        if not code:
            continue
        ae = t.parse_number(r.get(ae_c)) if ae_c else None
        # A&E performance is sometimes a 0..1 fraction; normalise to a percentage.
        if ae is not None and ae <= 1:
            ae *= 100
        rows.append(
            {
                "org_code": code,
                "provider_name": str(r.get(name_c) or "").strip() if name_c else None,
                "ae_4hr_pct": ae,
                "rtt_weeks": t.parse_number(r.get(rtt_c)) if rtt_c else None,
            }
        )
    return rows


def load_nhs_waiting(
    pool: ConnectionPool, url: str
) -> int:  # pragma: no cover - needs DB
    rows = _nhs_waiting_rows(_load_records(url))
    with pool.connection() as conn, conn.transaction():
        conn.execute("TRUNCATE nhs_waiting")
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO nhs_waiting "
                "(org_code, provider_name, ae_4hr_pct, rtt_weeks) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (org_code) DO UPDATE SET "
                "provider_name = EXCLUDED.provider_name, "
                "ae_4hr_pct = EXCLUDED.ae_4hr_pct, rtt_weeks = EXCLUDED.rtt_weeks",
                [
                    (r["org_code"], r["provider_name"], r["ae_4hr_pct"], r["rtt_weeks"])
                    for r in rows
                ],
            )
    return len(rows)


def load_crime(
    pool: ConnectionPool, url: str, area_type: str = "MSOA"
) -> int:  # pragma: no cover - PostGIS spatial join, exercised live
    points = _crime_points(_read_point_records(url))
    if not points:
        return 0
    with pool.connection() as conn, conn.transaction():
        conn.execute("CREATE TEMP TABLE _crime (lng float8, lat float8) ON COMMIT DROP")
        with conn.cursor() as cur:
            cur.executemany("INSERT INTO _crime VALUES (%s, %s)", points)
        conn.execute("DELETE FROM area_metric WHERE metric_key = 'crime_per_1k'")
        conn.execute(
            "INSERT INTO area_metric (area_code, area_type, metric_key, value) "
            "SELECT b.area_code, %s, 'crime_per_1k', "
            "round(1000.0 * count(*) / NULLIF(d.population, 0)) "
            "FROM _crime c JOIN geo_boundaries b "
            "ON b.area_type = %s AND ST_Contains("
            "b.geom, ST_SetSRID(ST_MakePoint(c.lng, c.lat), 4326)) "
            "JOIN census_demographics d ON d.area_code = b.area_code "
            "WHERE d.population > 0 "
            "GROUP BY b.area_code, d.population",
            [area_type, area_type],
        )
        n = conn.execute(
            "SELECT count(*) FROM area_metric WHERE metric_key = 'crime_per_1k'"
        ).fetchone()[0]
    return int(n)


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
    # Fetch once; if the user pasted the ONS dataset page, follow its download
    # link to the real file. Then parse by the resolved file's extension.
    data = _get_bytes(url)
    resolved = _resolve_data_url(url, data)
    if resolved:
        url = resolved
        data = _get_bytes(url)
    low = url.lower()
    if low.endswith(".xls"):
        records = _read_xls(data)
    elif low.endswith((".xlsx", ".xlsm")):
        records = _read_xlsx(data)
    else:
        records, _ = _read_csv(data.decode("utf-8-sig", "ignore"))
    rows = _house_price_rows(records, area_type)
    return _replace_table(
        pool,
        "house_prices",
        ("area_code", "area_type", "median_price"),
        rows,
        source="ONS HPSSA",
    )
