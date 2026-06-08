"""Reference data load jobs: dispatch, run and track status.

Loads run as background tasks in the worker and report status so the app can
show progress. Status is process-local (single worker replica); a load is a
rare, manual, idempotent operation so that is sufficient.
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
)

# dataset -> {status, rows, error, updatedAt}
_status: dict[str, dict] = {}


def get_status() -> dict[str, dict]:
    return _status


def _set(
    dataset: str, status: str, *, rows: int | None = None, error: str | None = None
) -> None:
    _status[dataset] = {
        "status": status,
        "rows": rows,
        "error": error,
        "updatedAt": datetime.now(UTC).isoformat(),
    }


def run_load(pool: ConnectionPool, dataset: str, params: dict) -> None:
    """Run one dataset load. Records status; never raises (errors are captured)."""
    _set(dataset, "running")
    area_type = params.get("areaType", "MSOA")
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
        else:
            raise ValueError(f"Unknown dataset: {dataset}")
        _set(dataset, "loaded", rows=n)
    except KeyError as exc:
        _set(dataset, "failed", error=f"Missing source URL: {exc}")
    except Exception as exc:  # capture download/parse/DB errors for the UI
        _set(dataset, "failed", error=str(exc))
