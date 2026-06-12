"""Server-side reference data loading (download and load, no local commands)."""

from .service import (
    DATASETS,
    UPLOAD_DATASETS,
    get_health,
    get_status,
    run_load,
    run_upload,
)

__all__ = [
    "DATASETS",
    "UPLOAD_DATASETS",
    "get_health",
    "get_status",
    "run_load",
    "run_upload",
]
