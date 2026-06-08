"""Worker HTTP surface.

The Next.js API layer submits catchment jobs and reads results here. The heavy
geospatial work runs in this worker via the orchestrator, never in a Next.js
request cycle (CLAUDE.md, architecture rules). Jobs run as background tasks: the
POST returns 202 with an id immediately, and the client polls the catchment for
status and results.

Dependencies (connection pool, store, isochrone provider and cache, reference
data) are built lazily from settings and cached as process singletons, so the
module imports without a database for the unit tests.
"""

from __future__ import annotations

import uuid

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException

from .api_models import CatchmentJobRequest, to_development_info, to_scoring_config
from .config import settings
from .pipeline.isochrone import (
    InMemoryIsochroneCache,
    OpenRouteServiceProvider,
    PostgresIsochroneCache,
)
from .pipeline.orchestrate import PipelineDeps, run_catchment
from .pipeline.reference import PostgresReferenceData
from .scoring.profile import ScoringConfig
from .storage import InMemoryStore, JobInput, PostgresStore, Storage

app = FastAPI(title="LandLynk worker", version="0.1.0")

# Process singletons, built lazily. Tests override _store before issuing requests.
_pool = None
_store: Storage | None = None
_cache = None


def get_pool():  # pragma: no cover - needs a database
    global _pool
    if _pool is None:
        from psycopg_pool import ConnectionPool

        _pool = ConnectionPool(settings.database_url, min_size=1, max_size=10)
    return _pool


def get_store() -> Storage:
    global _store
    if _store is None:
        _store = (
            PostgresStore(get_pool()) if settings.persist_results else InMemoryStore()
        )
    return _store


def get_cache():  # pragma: no cover - selects durable cache in production
    global _cache
    if _cache is None:
        _cache = (
            PostgresIsochroneCache(get_pool())
            if settings.persist_results
            else InMemoryIsochroneCache()
        )
    return _cache


def get_deps() -> PipelineDeps:  # pragma: no cover - needs external services
    client = httpx.Client(timeout=30.0)
    provider = OpenRouteServiceProvider(
        api_key=settings.isochrone_api_key,
        client=client,
        base_url=settings.isochrone_base_url,
    )
    return PipelineDeps(
        isochrone_provider=provider,
        isochrone_cache=get_cache(),
        reference=PostgresReferenceData(get_pool()),
    )


def _run_job(
    job_id: str, request: CatchmentJobRequest, config: ScoringConfig
) -> None:  # pragma: no cover - exercised via the app test with stubs
    store = get_store()
    store.mark_status(job_id, "running")
    try:
        result = run_catchment(
            raw_input=request.value,
            development=to_development_info(request),
            config=config,
            deps=get_deps(),
            area_type=request.area_type,
        )
        store.save_result(job_id, result, config)
    except Exception as exc:  # surface on the job, do not crash the worker
        store.mark_status(job_id, "failed", str(exc))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/jobs/catchment", status_code=202)
def submit_catchment_job(
    request: CatchmentJobRequest, background: BackgroundTasks
) -> dict[str, str]:
    job_id = str(uuid.uuid4())
    config = to_scoring_config(request)
    get_store().create_job(
        job_id,
        JobInput(
            kind=request.kind,
            value=request.value,
            development_name=request.development_name,
        ),
        config,
        created_by="system",
    )
    background.add_task(_run_job, job_id, request, config)
    return {"id": job_id}


@app.get("/catchments/{catchment_id}")
def get_catchment(catchment_id: str) -> dict:
    data = get_store().get_catchment(catchment_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Catchment not found")
    return data


@app.get("/catchments/{catchment_id}/battlecards/{area_code}")
def get_battlecard(catchment_id: str, area_code: str) -> dict:
    data = get_store().get_battlecard(catchment_id, area_code)
    if data is None:
        raise HTTPException(status_code=404, detail="Battlecard not found")
    return data
