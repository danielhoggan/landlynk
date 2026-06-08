"""Worker HTTP surface.

The Next.js API layer submits catchment jobs and reads results here. Long
running geospatial work happens in this worker, never in a Next.js request
cycle (CLAUDE.md, architecture rules). Job execution and persistence are wired
to Postgres and a job runner in implementation; this module defines the
contract the web client (``web/src/lib/workerClient.ts``) expects.
"""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="landlynk worker", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/jobs/catchment", status_code=202)
def submit_catchment_job() -> dict[str, str]:
    """Accept a catchment job and return its id.

    The full handler validates the input, creates a `catchment` row, enqueues
    the pipeline (resolve, isochrone, intersect, join, score, assemble) and
    returns immediately. Stubbed until the job runner and database are wired.
    """
    raise NotImplementedError("Catchment job runner not yet wired")


@app.get("/catchments/{catchment_id}")
def get_catchment(catchment_id: str) -> dict[str, str]:
    """Return a catchment with its scored, ranked areas. Stubbed."""
    raise NotImplementedError("Catchment reads not yet wired")


@app.get("/catchments/{catchment_id}/battlecards/{area_code}")
def get_battlecard(catchment_id: str, area_code: str) -> dict[str, str]:
    """Return one area's stored Battlecard payload. Stubbed."""
    raise NotImplementedError("Battlecard reads not yet wired")
