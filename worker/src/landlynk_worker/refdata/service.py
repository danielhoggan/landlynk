"""Reference data load jobs: dispatch, run and track status.

Loads run as background tasks in the worker. Status is persisted in the
reference_loads table so it survives a worker redeploy: the loaded data lives in
its own tables on the database volume, and recording the load status alongside
it means the app shows what is actually loaded rather than resetting to empty on
every restart. A process-local mirror covers the transient "running" state and
acts as a fallback when the database cannot be read.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from . import loaders

if TYPE_CHECKING:
    from psycopg_pool import ConnectionPool

DATASETS = (
    "geo_boundaries",
    "census_demographics",
    "census_tenure",
    "income_estimates",
    "house_prices",
    "green_space",
    "imd",
    "schools",
    "crime",
    "postcodes",
    "hospitals",
    "development_sites",
    "site_allocations",
    "planning_permissions",
)

# dataset -> {status, rows, error, areaType, updatedAt}. Mirror of the table for
# the live "running" state and a fallback when the database cannot be read.
_status: dict[str, dict] = {}


def get_status(pool: ConnectionPool | None = None) -> dict[str, dict]:
    """Return load status per dataset, preferring the persisted table.

    Falls back to the process-local mirror when no pool is given or the read
    fails, so the endpoint never errors just because the database is briefly
    unavailable.
    """
    if pool is None:
        return _status
    try:
        with pool.connection() as conn:
            rows = conn.execute(
                "SELECT dataset, status, rows, error, area_type, updated_at "
                "FROM reference_loads"
            ).fetchall()
    except Exception:
        return _status
    persisted = {
        dataset: {
            "status": status,
            "rows": n,
            "error": error,
            "areaType": area_type,
            "updatedAt": updated_at.isoformat() if updated_at else None,
        }
        for (dataset, status, n, error, area_type, updated_at) in rows
    }
    # A load in flight only exists in memory until it finishes; let it show.
    for dataset, mem in _status.items():
        if mem.get("status") == "running":
            persisted[dataset] = mem
    return persisted


def get_health(pool: ConnectionPool | None = None) -> dict:
    """A RAG summary of reference loading, safe for any user (no sources).

    green when every dataset is loaded, amber when some are (or a load is in
    flight), red when none are. Also lists loaded datasets that are older than
    their expected refresh cadence (stale), so admins can be nudged to reload.
    Carries only counts and dataset keys, never source URLs.
    """
    from datetime import timedelta

    status = get_status(pool)
    total = len(DATASETS)
    loaded = sum(1 for d in DATASETS if status.get(d, {}).get("status") == "loaded")
    running = any(status.get(d, {}).get("status") == "running" for d in DATASETS)
    if loaded == total:
        state = "green"
    elif loaded > 0 or running:
        state = "amber"
    else:
        state = "red"

    now = datetime.now(UTC)
    stale: list[str] = []
    for d in DATASETS:
        s = status.get(d, {})
        if s.get("status") != "loaded" or not s.get("updatedAt"):
            continue
        try:
            when = datetime.fromisoformat(s["updatedAt"])
            if when.tzinfo is None:
                when = when.replace(tzinfo=UTC)
        except (ValueError, TypeError):
            continue
        if now - when > timedelta(days=_MAX_AGE_DAYS.get(d, _DEFAULT_MAX_AGE_DAYS)):
            stale.append(d)
    return {"state": state, "loaded": loaded, "total": total, "stale": stale}


# How long a loaded dataset stays fresh before admins are nudged to recheck the
# source for a newer release, by the source's typical publication cadence.
_DEFAULT_MAX_AGE_DAYS = 365
_MAX_AGE_DAYS = {
    "geo_boundaries": 3650,
    "census_demographics": 3650,
    "census_tenure": 3650,
    "income_estimates": 400,
    "house_prices": 120,
    "green_space": 1100,
    "imd": 1500,
    "schools": 120,
    "crime": 60,
    "postcodes": 200,
    "hospitals": 365,
}


def _set(
    dataset: str,
    status: str,
    *,
    pool: ConnectionPool | None = None,
    rows: int | None = None,
    error: str | None = None,
    area_type: str | None = None,
) -> None:
    _status[dataset] = {
        "status": status,
        "rows": rows,
        "error": error,
        "areaType": area_type,
        "updatedAt": datetime.now(UTC).isoformat(),
    }
    if pool is None:
        return
    try:
        with pool.connection() as conn:
            conn.execute(
                "INSERT INTO reference_loads "
                "(dataset, status, rows, error, area_type, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, now()) "
                "ON CONFLICT (dataset) DO UPDATE SET "
                "status = EXCLUDED.status, rows = EXCLUDED.rows, "
                "error = EXCLUDED.error, area_type = EXCLUDED.area_type, "
                "updated_at = now()",
                [dataset, status, rows, error, area_type],
            )
    except Exception:
        # Status persistence is best effort; the load itself is what matters.
        pass


def run_load(pool: ConnectionPool, dataset: str, params: dict) -> None:
    """Run one dataset load. Records status; never raises (errors are captured)."""
    area_type = params.get("areaType", "MSOA")
    _set(dataset, "running", pool=pool, area_type=area_type)
    try:
        if dataset == "geo_boundaries":
            n = loaders.load_boundaries(pool, params["url"], area_type)
        elif dataset == "census_demographics":
            n = loaders.load_demographics(
                pool, params["ageUrl"], params["householdsUrl"], area_type
            )
        elif dataset == "census_tenure":
            n = loaders.load_tenure(pool, params["url"], area_type)
        elif dataset == "income_estimates":
            n = loaders.load_income(pool, params["url"], area_type)
        elif dataset == "house_prices":
            n = loaders.load_house_prices(pool, params["url"], area_type)
        elif dataset == "green_space":
            n = loaders.load_green_space(pool, params["url"], area_type)
        elif dataset == "imd":
            n = loaders.load_imd(
                pool, params["url"], params.get("lookupUrl"), area_type
            )
        elif dataset == "schools":
            n = loaders.load_schools(
                pool,
                params["url"],
                params.get("ratingsUrl") or None,
                area_type,
            )
        elif dataset == "crime":
            n = loaders.load_crime(pool, params["url"], area_type)
        elif dataset == "postcodes":
            n = loaders.load_postcodes(pool, params["url"])
        elif dataset == "hospitals":
            n = loaders.load_hospitals(pool, params["url"], area_type)
        elif dataset == "development_sites":
            n = loaders.load_development_sites(pool, params["url"], area_type)
        elif dataset == "site_allocations":
            n = loaders.load_site_allocations(pool, params["url"], area_type)
        elif dataset == "planning_permissions":
            n = loaders.load_planning_permissions(pool, params["url"], area_type)
        else:
            raise ValueError(f"Unknown dataset: {dataset}")
        _set(dataset, "loaded", pool=pool, rows=n, area_type=area_type)
    except KeyError as exc:
        _set(dataset, "failed", pool=pool, error=f"Missing source URL: {exc}")
    except Exception as exc:  # capture download/parse/DB errors for the UI
        _set(dataset, "failed", pool=pool, error=str(exc))


# Datasets that accept a manually downloaded file uploaded from the browser,
# rather than a URL the worker fetches. data.police.uk only offers custom-built
# downloads (no stable URL), and the ONS green space workbook is easier to grab
# by hand than to resolve from the dataset page, so both can be uploaded.
UPLOAD_DATASETS = ("crime", "green_space")


def run_upload_file(
    pool: ConnectionPool, dataset: str, filename: str, path: str, params: dict
) -> None:
    """Load one dataset from an uploaded file on disk, deleting the temp file
    afterwards. The file is streamed from disk (never wholly in memory), so a
    multi-GB crime archive loads without exhausting the worker. Records status;
    never raises."""
    import os

    area_type = params.get("areaType", "MSOA")
    _set(dataset, "running", pool=pool, area_type=area_type)
    try:
        if dataset == "crime":
            n = loaders.load_crime_file(pool, path, filename, area_type)
        elif dataset == "green_space":
            with open(path, "rb") as f:
                data = f.read()
            n = loaders.load_green_space_bytes(pool, filename, data, area_type)
        else:
            raise ValueError(f"Dataset does not support upload: {dataset}")
        _set(dataset, "loaded", pool=pool, rows=n, area_type=area_type)
    except Exception as exc:  # capture parse/DB errors for the UI
        _set(dataset, "failed", pool=pool, error=str(exc))
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
