"""Worker HTTP surface.

The Next.js API layer submits catchment jobs and reads results here. The heavy
geospatial work runs in this worker via the orchestrator, never in a Next.js
request cycle (CLAUDE.md, architecture rules). Jobs run as background tasks: the
POST returns 202 with an id immediately, and the client polls the catchment for
status and results.

Dependencies (isochrone provider and cache, reference data) are built from
settings. The isochrone cache is a process singleton so repeat runs in the same
worker reuse it; a durable Postgres cache is the production upgrade.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException

from .api_models import CatchmentJobRequest, to_development_info, to_scoring_config
from .config import settings
from .pipeline.isochrone import InMemoryIsochroneCache, OpenRouteServiceProvider
from .pipeline.orchestrate import CatchmentResult, PipelineDeps, run_catchment
from .pipeline.reference import PostgresReferenceData

app = FastAPI(title="LandLynk worker", version="0.1.0")

# Process-local isochrone cache, shared across requests in this worker.
_ISOCHRONE_CACHE = InMemoryIsochroneCache()


@dataclass
class JobRecord:
    request: CatchmentJobRequest
    status: str = "queued"
    result: CatchmentResult | None = None
    error: str | None = None
    created_by: str = "system"


_JOBS: dict[str, JobRecord] = {}


def _connection_factory() -> object:  # pragma: no cover - needs a database
    import psycopg

    return psycopg.connect(settings.database_url)


def build_deps() -> PipelineDeps:  # pragma: no cover - needs external services
    """Construct pipeline dependencies from settings."""
    client = httpx.Client(timeout=30.0)
    provider = OpenRouteServiceProvider(
        api_key=settings.isochrone_api_key, client=client
    )
    reference = PostgresReferenceData(_connection_factory)
    return PipelineDeps(
        isochrone_provider=provider,
        isochrone_cache=_ISOCHRONE_CACHE,
        reference=reference,
    )


def _run_job(job_id: str) -> None:  # pragma: no cover - needs external services
    job = _JOBS[job_id]
    job.status = "running"
    try:
        result = run_catchment(
            raw_input=job.request.value,
            development=to_development_info(job.request),
            config=to_scoring_config(job.request),
            deps=build_deps(),
            area_type=job.request.area_type,
        )
        job.result = result
        job.status = "complete"
    except Exception as exc:  # surface the failure on the job, do not crash
        job.error = str(exc)
        job.status = "failed"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/jobs/catchment", status_code=202)
def submit_catchment_job(
    request: CatchmentJobRequest, background: BackgroundTasks
) -> dict[str, str]:
    job_id = str(uuid.uuid4())
    _JOBS[job_id] = JobRecord(request=request)
    background.add_task(_run_job, job_id)
    return {"id": job_id}


@app.get("/catchments/{catchment_id}")
def get_catchment(catchment_id: str) -> dict:
    job = _JOBS.get(catchment_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Catchment not found")
    return serialise_catchment(catchment_id, job)


@app.get("/catchments/{catchment_id}/battlecards/{area_code}")
def get_battlecard(catchment_id: str, area_code: str) -> dict:
    job = _JOBS.get(catchment_id)
    if job is None or job.result is None:
        raise HTTPException(status_code=404, detail="Catchment not ready")
    card = job.result.battlecards.get(area_code)
    if card is None:
        raise HTTPException(status_code=404, detail="Battlecard not found")
    return card.model_dump(by_alias=True)


def serialise_catchment(catchment_id: str, job: JobRecord) -> dict:
    """Shape a job into the web Catchment contract (catchment.ts)."""
    result = job.result
    areas = []
    if result is not None:
        for area in result.areas:
            areas.append(
                {
                    "areaCode": area.area_code,
                    "areaType": area.area_type,
                    "name": area.name,
                    "proportionInside": round(area.proportion_inside, 4),
                    "score": round(area.score.total, 4),
                    "band": area.score.band,
                    "rank": area.rank,
                }
            )
    return {
        "id": catchment_id,
        "input": {
            "kind": job.request.kind,
            "value": job.request.value,
            "developmentName": job.request.development_name,
        },
        "coordinate": (
            None
            if result is None
            else {"lat": result.coordinate.lat, "lng": result.coordinate.lng}
        ),
        "isochrone": None if result is None else result.isochrone,
        "status": job.status,
        "areas": areas,
        "error": job.error,
    }
