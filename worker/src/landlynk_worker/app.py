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

import json
import logging
import uuid
from typing import TYPE_CHECKING

import httpx
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
    Response,
)
from pydantic import BaseModel, Field

from . import refdata
from .api_models import CatchmentJobRequest, to_development_info, to_scoring_config
from .battlecard import (
    Battlecard,
    render_battlecard_pdf,
    render_battlecard_pptx,
    render_battlecards_pdf,
    render_battlecards_pptx,
    render_report_pptx,
)
from .config import settings
from .pipeline.isochrone import (
    InMemoryIsochroneCache,
    IsochroneCache,
    OpenRouteServiceProvider,
    PostgresIsochroneCache,
)

if TYPE_CHECKING:
    from psycopg_pool import ConnectionPool
from .pipeline.orchestrate import PipelineDeps, run_catchment
from .pipeline.outputs.kml import render_catchment_kml
from .pipeline.reference import PostgresReferenceData
from .scoring.profile import ScoringConfig
from .storage import InMemoryStore, JobInput, PostgresStore, Storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
_log = logging.getLogger("landlynk.worker")

app = FastAPI(title="LandLynk worker", version="0.1.0")

# Process singletons, built lazily. Tests override _store before issuing requests.
_pool = None
_store: Storage | None = None
_cache = None


def get_pool() -> ConnectionPool:  # pragma: no cover - needs a database
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


def get_cache() -> IsochroneCache:  # pragma: no cover - durable cache in production
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
        _log.info("Catchment job %s complete: %s areas", job_id, len(result.areas))
    except Exception as exc:  # surface on the job, do not crash the worker
        _log.exception("Catchment job %s failed", job_id)
        store.mark_status(job_id, "failed", str(exc))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/segments")
def list_segments_endpoint(industry: str | None = None) -> list[dict]:
    """The predefined audience segments for segment-first targeting, filtered to
    an industry when given (the active brand's sector), else all sectors."""
    from .scoring.segments import list_segments

    return list_segments(industry)


@app.get("/objectives")
def list_objectives_endpoint() -> list[dict]:
    """The business objectives for objective-first targeting (with weight presets)."""
    from .scoring.objectives import list_objectives

    return list_objectives()


def _check_admin(token: str | None) -> None:
    if settings.admin_token and token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")


def current_user(
    x_user_email: str | None = Header(default=None),
    x_user_name: str | None = Header(default=None),
    x_active_brand: str | None = Header(default=None),
) -> dict:
    """Resolve the caller from the SSO-gated web layer's forwarded headers.

    The web service authenticates via Azure AD and forwards the signed-in
    identity, plus the brand the user has selected as active (X-Active-Brand),
    which scopes profiles and the AI allowance to that brand's group. The worker
    is private, so it trusts these headers. Each call upserts the user, applying
    the admin bootstrap from settings.admin_emails.
    """
    if not x_user_email:
        return {"email": None, "name": None, "role": "internal-user"}
    email = x_user_email.strip().lower()
    admin = email in settings.admin_email_set()
    try:
        user = get_store().upsert_user(email, x_user_name, admin)
    except Exception:  # never block a request on the user directory
        _log.exception("upsert_user failed for %s", email)
        user = {
            "email": email,
            "name": x_user_name,
            "role": "admin" if admin else "internal-user",
        }
    user["activeBrandId"] = x_active_brand or None
    return user


def _require_admin(user: dict) -> None:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")


def _audit(
    user: dict,
    action: str,
    *,
    target_type: str | None = None,
    target_id: str | None = None,
    detail: dict | None = None,
    cost: float = 0,
) -> None:
    """Append an audit entry. Never raises: auditing must not break the action."""
    try:
        get_store().record_audit(
            {
                "actorEmail": user.get("email"),
                "action": action,
                "targetType": target_type,
                "targetId": target_id,
                "detail": detail,
                "cost": cost,
            }
        )
    except Exception:  # pragma: no cover - best effort
        _log.exception("audit write failed for %s", action)


@app.get("/admin/costs")
def admin_costs(
    date_from: str | None = None,
    date_to: str | None = None,
    user: dict = Depends(current_user),
) -> dict:
    """AI cost report: totals and breakdowns by user, model and brand group."""
    _require_admin(user)
    store = get_store()
    report = store.cost_report(date_from, date_to)
    # Resolve group ids to names for the brand breakdown and line items.
    names = {g["id"]: g["name"] for g in store.list_builder_groups()}
    for row in report.get("byGroup", []):
        row["groupName"] = names.get(row.get("groupId"), "Internal / none")
    for item in report.get("items", []):
        item["groupName"] = names.get(item.get("groupId"), "Internal / none")
    return report


@app.get("/admin/audit")
def admin_audit(
    actor: str | None = None,
    action: str | None = None,
    min_cost: float | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    user: dict = Depends(current_user),
) -> list[dict]:
    """Filterable audit trail for the admin Audits tab."""
    _require_admin(user)
    return get_store().list_audit(
        {
            "actor": actor,
            "action": action,
            "minCost": min_cost,
            "dateFrom": date_from,
            "dateTo": date_to,
        }
    )


def _require_owner_or_admin(catchment_id: str, user: dict) -> None:
    if user.get("role") == "admin":
        return
    owner = get_store().get_owner(catchment_id)
    if owner is None or owner != user.get("email"):
        raise HTTPException(status_code=403, detail="Not your catchment")


def _require_access(catchment_id: str, user: dict) -> None:
    """Opening a run is governed by ownership and in-portal sharing, not by
    holding its id. Owner, anyone it is shared with, or an admin may read it."""
    if not get_store().can_access(
        catchment_id, user.get("email"), user.get("role") == "admin"
    ):
        raise HTTPException(status_code=403, detail="No access to this catchment")


@app.get("/reference/health")
def reference_health(user: dict = Depends(current_user)) -> dict:
    """RAG summary of reference loading for the status dot. No source detail, so
    any signed-in user may read it; the full provenance stays admin only."""
    pool = None
    if settings.persist_results:
        try:
            pool = get_pool()
        except Exception:
            pool = None
    return refdata.get_health(pool)


@app.get("/admin/reference/status")
def reference_status(x_admin_token: str | None = Header(default=None)) -> dict:
    _check_admin(x_admin_token)
    pool = None
    if settings.persist_results:
        try:
            pool = get_pool()
        except Exception:  # status falls back to the in-memory mirror
            pool = None
    return refdata.get_status(pool)


@app.post("/admin/reference/{dataset}", status_code=202)
def load_reference(
    dataset: str,
    params: dict,
    background: BackgroundTasks,
    x_admin_token: str | None = Header(default=None),
) -> dict[str, str]:
    """Download and load one reference dataset into PostGIS, in the background."""
    _check_admin(x_admin_token)
    if dataset not in refdata.DATASETS:
        raise HTTPException(status_code=404, detail=f"Unknown dataset: {dataset}")
    background.add_task(refdata.run_load, get_pool(), dataset, params or {})
    return {"status": "started", "dataset": dataset}


@app.post("/admin/reference/{dataset}/upload-chunk", status_code=202)
async def upload_reference_chunk(
    dataset: str,
    request: Request,
    background: BackgroundTasks,
    x_upload_id: str = Header(...),
    x_chunk_index: int = Header(...),
    x_total_chunks: int = Header(...),
    x_filename: str = Header("upload.dat"),
    x_area_type: str = Header("MSOA"),
    x_admin_token: str | None = Header(default=None),
) -> dict[str, str | int]:
    """Receive one chunk of an uploaded reference file (e.g. a data.police.uk
    crime archive) and append it to a temp file on disk. Chunking lets an admin
    upload a multi-GB file straight from the browser without hitting platform
    request size or timeout limits, and without any external storage. When the
    last chunk arrives the background load streams the assembled file from disk
    and deletes it. The browser sends chunks strictly in order."""
    import os
    import re
    import tempfile
    from urllib.parse import unquote

    _check_admin(x_admin_token)
    if dataset not in refdata.UPLOAD_DATASETS:
        raise HTTPException(
            status_code=404, detail=f"Dataset does not support upload: {dataset}"
        )
    if x_total_chunks < 1 or not 0 <= x_chunk_index < x_total_chunks:
        raise HTTPException(status_code=400, detail="Bad chunk index")
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "", x_upload_id)[:64]
    if not safe_id:
        raise HTTPException(status_code=400, detail="Bad upload id")
    filename = os.path.basename(unquote(x_filename)) or "upload.dat"
    suffix = os.path.splitext(filename)[1] or ".dat"
    path = os.path.join(tempfile.gettempdir(), f"landlynk-upload-{safe_id}{suffix}")
    # First chunk truncates; later chunks append. A later chunk with no file
    # means an earlier one was lost, so the upload must restart.
    if x_chunk_index > 0 and not os.path.exists(path):
        raise HTTPException(status_code=409, detail="Missing earlier chunk; restart")
    with open(path, "wb" if x_chunk_index == 0 else "ab") as out:
        async for chunk in request.stream():
            out.write(chunk)
    if x_chunk_index + 1 < x_total_chunks:
        return {"status": "received", "chunk": x_chunk_index}
    background.add_task(
        refdata.run_upload_file,
        get_pool(),
        dataset,
        filename,
        path,
        {"areaType": x_area_type},
    )
    return {"status": "started", "dataset": dataset}


@app.post("/jobs/catchment", status_code=202)
def submit_catchment_job(
    request: CatchmentJobRequest,
    background: BackgroundTasks,
    user: dict = Depends(current_user),
) -> dict[str, str]:
    # External users draw each run from a monthly allowance pooled per their
    # active brand's group; internal users and admins are unmetered.
    _enforce_job_quota(user)
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
        created_by=user.get("email") or "system",
    )
    # Record the run against the allowance now, on submission. This is an
    # append-only tally, so deleting or archiving the catchment later never
    # reclaims the run.
    get_store().record_job_usage(
        user.get("email"), _active_group(user), job_id, _usage_period()
    )
    background.add_task(_run_job, job_id, request, config)
    _audit(
        user,
        "run.create",
        target_type="catchment",
        target_id=job_id,
        detail={"development": request.development_name, "input": request.value},
    )
    return {"id": job_id}


@app.get("/catchments")
def list_catchments(
    archived: bool = False, limit: int = 100, user: dict = Depends(current_user)
) -> list[dict]:
    return get_store().list_catchments(
        user.get("email"), user.get("role") == "admin", archived=archived, limit=limit
    )


@app.get("/catchments/{catchment_id}")
def get_catchment(catchment_id: str, user: dict = Depends(current_user)) -> dict:
    data = get_store().get_catchment(catchment_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Catchment not found")
    _require_access(catchment_id, user)
    return data


@app.delete("/catchments/{catchment_id}", status_code=204)
def delete_catchment(catchment_id: str, user: dict = Depends(current_user)) -> Response:
    # Only admins delete. Everyone else archives (hide, never destroy).
    _require_admin(user)
    if not get_store().delete_catchment(catchment_id):
        raise HTTPException(status_code=404, detail="Catchment not found")
    _audit(user, "run.delete", target_type="catchment", target_id=catchment_id)
    return Response(status_code=204)


@app.post("/catchments/{catchment_id}/archive", status_code=204)
def archive_catchment(
    catchment_id: str, user: dict = Depends(current_user)
) -> Response:
    _require_owner_or_admin(catchment_id, user)
    if not get_store().set_archived(catchment_id, True):
        raise HTTPException(status_code=404, detail="Catchment not found")
    return Response(status_code=204)


@app.post("/catchments/{catchment_id}/unarchive", status_code=204)
def unarchive_catchment(
    catchment_id: str, user: dict = Depends(current_user)
) -> Response:
    _require_owner_or_admin(catchment_id, user)
    if not get_store().set_archived(catchment_id, False):
        raise HTTPException(status_code=404, detail="Catchment not found")
    return Response(status_code=204)


class ShareRequest(BaseModel):
    emails: list[str]


@app.get("/catchments/{catchment_id}/shares")
def list_shares(catchment_id: str, user: dict = Depends(current_user)) -> list[str]:
    _require_owner_or_admin(catchment_id, user)
    return get_store().list_shares(catchment_id)


@app.post("/catchments/{catchment_id}/shares", status_code=204)
def add_shares(
    catchment_id: str, request: ShareRequest, user: dict = Depends(current_user)
) -> Response:
    _require_owner_or_admin(catchment_id, user)
    get_store().add_shares(catchment_id, request.emails)
    return Response(status_code=204)


@app.delete("/catchments/{catchment_id}/shares/{email}", status_code=204)
def remove_share(
    catchment_id: str, email: str, user: dict = Depends(current_user)
) -> Response:
    _require_owner_or_admin(catchment_id, user)
    get_store().remove_share(catchment_id, email)
    return Response(status_code=204)


@app.get("/me")
def get_me(user: dict = Depends(current_user)) -> dict:
    # The brands this user may switch between (whole-group grant plus any granted
    # brands). The web picks an active one and white-labels the shell from it.
    email = user.get("email")
    brands = get_store().get_accessible_brands(email) if email else []
    return {**user, "brands": brands}


@app.get("/me/settings")
def get_my_settings(user: dict = Depends(current_user)) -> dict:
    email = user.get("email")
    settings_doc = get_store().get_settings(email) if email else None
    return {"settings": settings_doc}


@app.put("/me/settings", status_code=204)
def put_my_settings(payload: dict, user: dict = Depends(current_user)) -> Response:
    email = user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="No user identity")
    get_store().save_settings(email, payload.get("settings") or {})
    return Response(status_code=204)


@app.get("/admin/users")
def admin_list_users(user: dict = Depends(current_user)) -> list[dict]:
    _require_admin(user)
    return get_store().list_users()


# --- builder profiles -------------------------------------------------------


def _active_group(user: dict) -> str | None:
    """The group of the user's active brand, validated against the brands they
    may access, falling back to their whole-group grant. Drives profile scoping
    and the AI allowance, so a user switching brand switches client context."""
    bid = user.get("activeBrandId")
    email = user.get("email")
    if bid and email:
        for b in get_store().get_accessible_brands(email):
            if b["builderId"] == bid:
                return b["groupId"]
    return user.get("builderGroupId")


def _scope_group(user: dict) -> str | None:
    """The group a user is restricted to, or None to see all profiles.

    Admins are unscoped. Everyone else is scoped to their active brand's group
    (or their whole-group grant), so they see only that client's profiles.
    """
    if user.get("role") == "admin":
        return None
    return _active_group(user)


def _usage_period() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("%Y-%m")


def _next_reset_date() -> str:
    """ISO date the monthly AI allowance resets: the 1st of next month, UTC."""
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    year, month = (now.year + 1, 1) if now.month == 12 else (now.year, now.month + 1)
    return f"{year:04d}-{month:02d}-01"


def _group_cap(group_id: str) -> int | None:
    for g in get_store().list_builder_groups():
        if g["id"] == group_id:
            return g.get("monthlyCap")
    return None


def _llm_usage_summary(user: dict) -> dict:
    """Remaining AI allowance for the caller. Internal users are unlimited.

    estCost is the indicative GBP cost of one generation with the default model,
    so the UI can flag the cost before a user runs a lookup.
    """
    from .enrichment import model_cost

    period = _usage_period()
    model = _default_model()
    est_cost = model_cost(model) if model else 0.0
    group_id = _active_group(user)
    if user.get("role") == "admin" or not group_id:
        return {
            "period": period,
            "metered": False,
            "cap": None,
            "used": 0,
            "model": model,
            "estCost": est_cost,
            "resetsOn": _next_reset_date(),
        }
    cap = _group_cap(group_id)
    used = get_store().llm_usage_count(group_id, period)
    remaining = None if cap is None else max(cap - used, 0)
    return {
        "period": period,
        "metered": True,
        "cap": cap,
        "used": used,
        "remaining": remaining,
        "model": model,
        "estCost": est_cost,
        "resetsOn": _next_reset_date(),
    }


def _enforce_llm_quota(user: dict) -> None:
    """Block an external user whose group has spent its monthly allowance."""
    summary = _llm_usage_summary(user)
    if (
        summary["metered"]
        and summary["cap"] is not None
        and summary["used"] >= summary["cap"]
    ):
        raise HTTPException(
            status_code=429,
            detail=(
                f"Monthly AI allowance reached ({summary['cap']}). "
                "It resets at the start of next month."
            ),
        )


def _group_job_cap(group_id: str) -> int | None:
    for g in get_store().list_builder_groups():
        if g["id"] == group_id:
            return g.get("monthlyJobCap")
    return None


def _job_usage_summary(user: dict) -> dict:
    """Remaining monthly catchment-run allowance for the caller. Pooled per the
    active brand's group, resets on the 1st, unmetered for internal users."""
    period = _usage_period()
    group_id = _active_group(user)
    if user.get("role") == "admin" or not group_id:
        return {
            "period": period,
            "metered": False,
            "cap": None,
            "used": 0,
            "resetsOn": _next_reset_date(),
        }
    cap = _group_job_cap(group_id)
    used = get_store().job_usage_count(group_id, period)
    remaining = None if cap is None else max(cap - used, 0)
    return {
        "period": period,
        "metered": True,
        "cap": cap,
        "used": used,
        "remaining": remaining,
        "resetsOn": _next_reset_date(),
    }


def _enforce_job_quota(user: dict) -> None:
    """Block an external user whose group has spent its monthly run allowance."""
    summary = _job_usage_summary(user)
    if (
        summary["metered"]
        and summary["cap"] is not None
        and summary["used"] >= summary["cap"]
    ):
        raise HTTPException(
            status_code=429,
            detail=(
                f"Monthly run allowance reached ({summary['cap']}). "
                "It resets at the start of next month."
            ),
        )


@app.get("/builders/usage")
def llm_usage(user: dict = Depends(current_user)) -> dict:
    """The caller's AI generation and catchment-run allowances this month. The
    AI allowance is flat at the top level (its long-standing shape); the run
    allowance is nested under ``jobs``."""
    return {**_llm_usage_summary(user), "jobs": _job_usage_summary(user)}


@app.get("/builders/profiles")
def list_profiles(user: dict = Depends(current_user)) -> list[dict]:
    """Targeting profiles the caller may use, scoped to their group if external."""
    return get_store().list_builder_profiles(_scope_group(user))


class GroupRequest(BaseModel):
    name: str | None = None
    monthly_cap: int | None = Field(default=None, alias="monthlyCap")
    monthly_job_cap: int | None = Field(default=None, alias="monthlyJobCap")
    industry: str | None = None

    model_config = {"populate_by_name": True}


@app.get("/admin/builders/groups")
def admin_groups(user: dict = Depends(current_user)) -> list[dict]:
    _require_admin(user)
    return get_store().list_builder_groups()


@app.post("/admin/builders/groups")
def admin_create_group(
    request: GroupRequest, user: dict = Depends(current_user)
) -> dict:
    _require_admin(user)
    group_id = str(uuid.uuid4())
    get_store().create_builder_group(
        group_id,
        request.name or "",
        request.monthly_cap,
        request.industry,
        monthly_job_cap=request.monthly_job_cap,
    )
    _audit(
        user,
        "builder.group.create",
        target_type="group",
        target_id=group_id,
        detail={
            "name": request.name,
            "monthlyCap": request.monthly_cap,
            "monthlyJobCap": request.monthly_job_cap,
        },
    )
    return {"id": group_id, "name": request.name}


@app.put("/admin/builders/groups/{group_id}", status_code=204)
def admin_update_group(
    group_id: str, request: GroupRequest, user: dict = Depends(current_user)
) -> Response:
    _require_admin(user)
    get_store().update_builder_group(
        group_id,
        request.name,
        request.monthly_cap,
        request.industry,
        monthly_job_cap=request.monthly_job_cap,
    )
    return Response(status_code=204)


@app.delete("/admin/builders/groups/{group_id}", status_code=204)
def admin_delete_group(group_id: str, user: dict = Depends(current_user)) -> Response:
    _require_admin(user)
    get_store().delete_builder_group(group_id)
    _audit(user, "builder.group.delete", target_type="group", target_id=group_id)
    return Response(status_code=204)


class BuilderRequest(BaseModel):
    group_id: str = Field(alias="groupId")
    name: str
    theme_heading: str = Field(default="#2F6B3A", alias="themeHeading")
    theme_secondary: str | None = Field(default=None, alias="themeSecondary")
    theme_accent: str | None = Field(default=None, alias="themeAccent")
    fonts: list[str] = []
    target_locations: list[str] = Field(default_factory=list, alias="targetLocations")
    industry: str | None = None

    model_config = {"populate_by_name": True}


@app.get("/admin/builders")
def admin_builders(
    group_id: str | None = None, user: dict = Depends(current_user)
) -> list[dict]:
    _require_admin(user)
    return get_store().list_builders(group_id)


@app.post("/admin/builders")
def admin_create_builder(
    request: BuilderRequest, user: dict = Depends(current_user)
) -> dict:
    _require_admin(user)
    builder_id = str(uuid.uuid4())
    get_store().create_builder(
        {
            "id": builder_id,
            "groupId": request.group_id,
            "name": request.name,
            "themeHeading": request.theme_heading,
            "themeSecondary": request.theme_secondary,
            "themeAccent": request.theme_accent,
            "fonts": request.fonts,
            "targetLocations": request.target_locations,
            "industry": request.industry,
        }
    )
    _audit(
        user,
        "builder.brand.create",
        target_type="brand",
        target_id=builder_id,
        detail={"name": request.name, "groupId": request.group_id},
    )
    return {"id": builder_id}


@app.delete("/admin/builders/{builder_id}", status_code=204)
def admin_delete_builder(
    builder_id: str, user: dict = Depends(current_user)
) -> Response:
    _require_admin(user)
    get_store().delete_builder(builder_id)
    _audit(user, "builder.brand.delete", target_type="brand", target_id=builder_id)
    return Response(status_code=204)


class LogoRequest(BaseModel):
    """A base64 logo upload for a brand (data only, no data: URL prefix)."""

    filename: str = "logo.png"
    content: str  # base64


class BuilderUpdateRequest(BaseModel):
    name: str | None = None
    theme_heading: str | None = Field(default=None, alias="themeHeading")
    theme_secondary: str | None = Field(default=None, alias="themeSecondary")
    theme_accent: str | None = Field(default=None, alias="themeAccent")
    fonts: list[str] | None = None
    target_locations: list[str] | None = Field(default=None, alias="targetLocations")
    industry: str | None = None

    model_config = {"populate_by_name": True}


@app.put("/admin/builders/{builder_id}", status_code=204)
def admin_update_builder(
    builder_id: str, request: BuilderUpdateRequest, user: dict = Depends(current_user)
) -> Response:
    """Edit a saved brand's name, colours, fonts, target locations or industry.
    Only the fields sent are changed; the logo is managed separately."""
    _require_admin(user)
    fields = request.model_dump(by_alias=True, exclude_unset=True)
    if not get_store().update_builder(builder_id, fields):
        raise HTTPException(status_code=404, detail="Brand not found")
    _audit(user, "builder.brand.update", target_type="brand", target_id=builder_id)
    return Response(status_code=204)


@app.post("/admin/builders/{builder_id}/logo")
def admin_upload_logo(
    builder_id: str, request: LogoRequest, user: dict = Depends(current_user)
) -> dict:
    import base64

    from . import assets

    _require_admin(user)
    builder = next(
        (b for b in get_store().list_builders() if b["id"] == builder_id), None
    )
    if builder is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    try:
        raw = base64.b64decode(request.content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid logo data") from exc
    ext = request.filename.rsplit(".", 1)[-1] if "." in request.filename else "png"
    path = assets.commit_logo(builder["name"], raw, ext)
    if path is None:
        raise HTTPException(
            status_code=503,
            detail="Logo storage not configured. Set the GitHub token.",
        )
    get_store().set_builder_logo(builder_id, path)
    _audit(user, "builder.brand.logo", target_type="brand", target_id=builder_id)
    return {"logoPath": path}


@app.get("/builders/{builder_id}/logo")
def get_builder_logo(builder_id: str, user: dict = Depends(current_user)) -> Response:
    from . import assets

    builder = next(
        (b for b in get_store().list_builders() if b["id"] == builder_id), None
    )
    if builder is None or not builder.get("logoPath"):
        raise HTTPException(status_code=404, detail="No logo")
    data = assets.fetch_logo(builder["logoPath"])
    if data is None:
        raise HTTPException(status_code=404, detail="Logo unavailable")
    ext = builder["logoPath"].rsplit(".", 1)[-1].lower()
    media = (
        "image/svg+xml"
        if ext == "svg"
        else f"image/{'jpeg' if ext in ('jpg','jpeg') else ext}"
    )
    return Response(content=data, media_type=media)


class ProfileRequest(BaseModel):
    id: str | None = None
    builder_id: str = Field(alias="builderId")
    name: str
    segment: str | None = None
    bed_range: str | None = Field(default=None, alias="bedRange")
    price_from: float | None = Field(default=None, alias="priceFrom")
    price_to: float | None = Field(default=None, alias="priceTo")
    strapline: str | None = None
    pillars: list[str] = []
    features: list[str] = []

    model_config = {"populate_by_name": True}


@app.post("/admin/builders/profiles")
def admin_save_profile(
    request: ProfileRequest, user: dict = Depends(current_user)
) -> dict:
    _require_admin(user)
    profile = request.model_dump(by_alias=True)
    profile["id"] = request.id or str(uuid.uuid4())
    get_store().upsert_builder_profile(profile)
    _audit(
        user,
        "builder.profile.save",
        target_type="profile",
        target_id=profile["id"],
        detail={"name": request.name},
    )
    return {"id": profile["id"]}


@app.delete("/admin/builders/profiles/{profile_id}", status_code=204)
def admin_delete_profile(
    profile_id: str, user: dict = Depends(current_user)
) -> Response:
    _require_admin(user)
    get_store().delete_builder_profile(profile_id)
    _audit(user, "builder.profile.delete", target_type="profile", target_id=profile_id)
    return Response(status_code=204)


class UserGroupRequest(BaseModel):
    group_id: str | None = Field(default=None, alias="groupId")

    model_config = {"populate_by_name": True}


@app.put("/admin/users/{email}/group", status_code=204)
def admin_set_user_group(
    email: str, request: UserGroupRequest, user: dict = Depends(current_user)
) -> Response:
    _require_admin(user)
    get_store().set_user_group(email, request.group_id)
    _audit(
        user,
        "user.group",
        target_type="user",
        target_id=email,
        detail={"groupId": request.group_id},
    )
    return Response(status_code=204)


class UserBrandsRequest(BaseModel):
    brand_ids: list[str] = Field(default_factory=list, alias="brandIds")

    model_config = {"populate_by_name": True}


@app.get("/admin/users/{email}/brands")
def admin_get_user_brands(
    email: str, user: dict = Depends(current_user)
) -> dict:
    """The specific brand grants for a user (separate from a whole-group grant)."""
    _require_admin(user)
    return {"brandIds": get_store().list_user_brand_ids(email)}


@app.put("/admin/users/{email}/brands", status_code=204)
def admin_set_user_brands(
    email: str, request: UserBrandsRequest, user: dict = Depends(current_user)
) -> Response:
    """Assign a user to specific brands (a business unit), which they can switch
    between. Independent of any whole-group grant set above."""
    _require_admin(user)
    get_store().set_user_brands(email, request.brand_ids)
    _audit(
        user,
        "user.brands",
        target_type="user",
        target_id=email,
        detail={"count": len(request.brand_ids)},
    )
    return Response(status_code=204)


def _default_model() -> str | None:
    from .enrichment import available_models
    from .enrichment.models import default_available_model

    stored = get_store().get_config("default_model")
    chosen = (stored or {}).get("model") if stored else None
    ids = {m["id"] for m in available_models()}
    if chosen in ids:
        return chosen
    return default_available_model()


def _objective_id(catchment: dict) -> str | None:
    """The business objective stored on a catchment, part of the AI cache key."""
    return ((catchment.get("input") or {}).get("config") or {}).get("objective")


def _area_profile_key(codes: list[str], model: str, objective_id: str | None) -> str:
    """Cache identity for an AI Local Area Profile: the area set, the model and
    the business objective (which frames the prompt). Shared by the generate,
    read and export paths so a cached profile is found consistently."""
    import hashlib

    key_src = "|".join(sorted(codes)) + "::" + model + "::" + (objective_id or "")
    return hashlib.sha256(key_src.encode()).hexdigest()


@app.get("/admin/models")
def admin_list_models(user: dict = Depends(current_user)) -> dict:
    """Available AI models (by configured provider keys) and the chosen default."""
    _require_admin(user)
    from .enrichment import available_models

    return {"models": available_models(), "default": _default_model()}


class DefaultModelRequest(BaseModel):
    model: str


@app.put("/admin/models/default", status_code=204)
def admin_set_default_model(
    request: DefaultModelRequest, user: dict = Depends(current_user)
) -> Response:
    _require_admin(user)
    from .enrichment import available_models

    if request.model not in {m["id"] for m in available_models()}:
        raise HTTPException(status_code=400, detail="Model not available")
    get_store().set_config("default_model", {"model": request.model})
    _audit(user, "ai.default_model", detail={"model": request.model})
    return Response(status_code=204)


class AreaProfileRequest(BaseModel):
    area_codes: list[str] = []
    scope: str = "whole"
    model: str | None = None
    refresh: bool = False


@app.post("/catchments/{catchment_id}/area-profile")
def area_profile(
    catchment_id: str,
    request: AreaProfileRequest,
    user: dict = Depends(current_user),
) -> dict:
    """Generate (or return cached) an AI Local Area Profile for the area set."""
    from .enrichment import generate_area_profile

    _require_access(catchment_id, user)
    store = get_store()
    catchment = store.get_catchment(catchment_id)
    if catchment is None:
        raise HTTPException(status_code=404, detail="Catchment not found")
    areas = catchment.get("areas", [])
    by_code = {a["areaCode"]: a.get("name", a["areaCode"]) for a in areas}
    if request.scope == "whole" or not request.area_codes:
        codes = [a["areaCode"] for a in areas]
    else:
        codes = [c for c in request.area_codes if c in by_code]
    if not codes:
        raise HTTPException(status_code=404, detail="No areas for the profile")

    model = request.model or _default_model()
    if not model:
        raise HTTPException(
            status_code=503, detail="No AI model configured. Add a provider key."
        )

    # The business objective frames the commentary, so it is part of the prompt
    # and therefore part of the cache identity.
    objective_id = _objective_id(catchment)
    objective_framing = None
    if objective_id:
        from .scoring.objectives import OBJECTIVES

        obj = OBJECTIVES.get(objective_id)
        objective_framing = obj.ai_framing if obj else None

    cache_key = _area_profile_key(codes, model, objective_id)
    if not request.refresh:
        cached = store.get_area_profile(cache_key)
        if cached is not None:
            return {**cached, "cached": True}

    # A real generation is about to hit the provider. Enforce the external-user
    # monthly allowance (pooled per builder group); internal users are unmetered.
    _enforce_llm_quota(user)

    # Anchor the prompt on the development's own location, not the list of
    # catchment area names. A 30-minute catchment spans several local
    # authorities, so a name list made the model place the scheme in the wrong
    # town. The postcode keeps it precise.
    inp = catchment.get("input") or {}
    dev_name = inp.get("developmentName") or "the development"
    postcode = inp.get("value") if inp.get("kind") == "postcode" else None
    if postcode:
        location = f"{dev_name}, {postcode}"
    else:
        # No postcode (grid reference): fall back to the development's home area.
        home = by_code.get(codes[0], codes[0])
        location = f"{dev_name}, {home}"
    try:
        extra = {"objective_framing": objective_framing} if objective_framing else {}
        payload = generate_area_profile(location, model, **extra)
    except Exception as exc:
        _log.exception("Area profile generation failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    from .enrichment import token_cost

    usage = payload.pop("usage", {}) or {}
    in_tok = int(usage.get("input", 0) or 0)
    out_tok = int(usage.get("output", 0) or 0)
    total_tok = int(usage.get("total", in_tok + out_tok) or 0)
    cost = token_cost(model, in_tok, out_tok)

    active_group = _active_group(user)
    store.record_llm_usage(user.get("email"), active_group, model, _usage_period())
    store.save_area_profile(cache_key, model, payload)
    _audit(
        user,
        "ai.generate",
        target_type="catchment",
        target_id=catchment_id,
        detail={
            "model": model,
            "areas": len(codes),
            "groupId": active_group,
            "tokens": total_tok,
            "inputTokens": in_tok,
            "outputTokens": out_tok,
        },
        cost=cost,
    )
    return {"model": model, **payload, "cached": False}


@app.get("/catchments/{catchment_id}/area-profile")
def cached_area_profile(
    catchment_id: str,
    scope: str = "whole",
    user: dict = Depends(current_user),
) -> dict:
    """Return an already-cached AI Local Area Profile for the whole catchment,
    or {"profile": None} if none exists. Read-only: never calls the provider and
    never touches the allowance, so a historic catchment can show its snapshot
    without the user clicking Add AI lookup."""
    _require_access(catchment_id, user)
    store = get_store()
    catchment = store.get_catchment(catchment_id)
    if catchment is None:
        raise HTTPException(status_code=404, detail="Catchment not found")
    codes = [a["areaCode"] for a in catchment.get("areas", [])]
    model = _default_model()
    if not codes or not model:
        return {"profile": None}
    key = _area_profile_key(codes, model, _objective_id(catchment))
    cached = store.get_area_profile(key)
    if cached is None:
        return {"profile": None}
    return {"profile": {"model": model, **cached, "cached": True}}


class RoleRequest(BaseModel):
    role: str


_ROLES = {"admin", "internal-user", "external-user"}


@app.put("/admin/users/{email}/role", status_code=204)
def admin_set_role(
    email: str, request: RoleRequest, user: dict = Depends(current_user)
) -> Response:
    _require_admin(user)
    if request.role not in _ROLES:
        raise HTTPException(status_code=400, detail=f"Unknown role: {request.role}")
    if not get_store().set_role(email, request.role):
        raise HTTPException(status_code=404, detail="User not found")
    _audit(
        user,
        "user.role",
        target_type="user",
        target_id=email,
        detail={"role": request.role},
    )
    return Response(status_code=204)


@app.get("/catchments/{catchment_id}/battlecards/{area_code}")
def get_battlecard(
    catchment_id: str, area_code: str, user: dict = Depends(current_user)
) -> dict:
    _require_access(catchment_id, user)
    data = get_store().get_battlecard(catchment_id, area_code)
    if data is None:
        raise HTTPException(status_code=404, detail="Battlecard not found")
    return data


@app.get("/catchments/{catchment_id}/kml")
def get_catchment_kml(
    catchment_id: str, user: dict = Depends(current_user)
) -> Response:
    _require_access(catchment_id, user)
    store = get_store()
    catchment = store.get_catchment(catchment_id)
    if catchment is None:
        raise HTTPException(status_code=404, detail="Catchment not found")
    battlecards = {
        area["areaCode"]: store.get_battlecard(catchment_id, area["areaCode"])
        for area in catchment.get("areas", [])
    }
    kml = render_catchment_kml(catchment, battlecards)
    return Response(
        content=kml,
        media_type="application/vnd.google-earth.kml+xml",
        headers={
            "Content-Disposition": f'attachment; filename="catchment-{catchment_id}.kml"'
        },
    )


class ShortlistRequest(BaseModel):
    """Selected areas to combine into one export document."""

    area_codes: list[str]


def _shortlist_cards(catchment_id: str, area_codes: list[str]) -> list[Battlecard]:
    """Fetch and validate the Battlecards for a shortlist, in the order given.

    Missing area codes are skipped rather than failing the whole export, so a
    stale selection still produces a document for the areas that resolve.
    """
    store = get_store()
    cards: list[Battlecard] = []
    for code in area_codes:
        data = store.get_battlecard(catchment_id, code)
        if data is not None:
            cards.append(Battlecard.model_validate(data))
    return cards


def _heading(catchment_id: str) -> str | None:
    """The brand heading colour stored with the run, for themed exports."""
    catchment = get_store().get_catchment(catchment_id)
    config = (catchment or {}).get("input", {}).get("config") or {}
    return config.get("brandHeading")


def _area_geometry(catchment_id: str, area_code: str) -> dict | None:
    """The GeoJSON for one area, for the export map thumbnail."""
    catchment = get_store().get_catchment(catchment_id)
    for area in (catchment or {}).get("areas", []):
        if area.get("areaCode") == area_code:
            return area.get("geometry")
    return None


def _catchment_geometry(catchment_id: str) -> dict | None:
    """The whole-catchment polygon (isochrone or radius) for the map thumbnail."""
    catchment = get_store().get_catchment(catchment_id)
    return (catchment or {}).get("isochrone")


def _brand_accent(catchment_id: str) -> str | None:
    catchment = get_store().get_catchment(catchment_id)
    return ((catchment or {}).get("input", {}).get("config") or {}).get("brandAccent")


def _brand_secondary(catchment_id: str) -> str | None:
    catchment = get_store().get_catchment(catchment_id)
    cfg = (catchment or {}).get("input", {}).get("config") or {}
    return cfg.get("brandSecondary")


def _catchment_coord(catchment_id: str) -> tuple[float | None, float | None]:
    catchment = get_store().get_catchment(catchment_id)
    coord = (catchment or {}).get("coordinate") or {}
    return coord.get("lat"), coord.get("lng")


def _development_context(catchment_id: str) -> dict | None:
    """Nearest hospital to the development and that provider's NHS waits, if
    loaded. Best effort: returns None without a coordinate, hospitals or DB."""
    lat, lng = _catchment_coord(catchment_id)
    if lat is None or lng is None:
        return None
    try:
        with get_pool().connection() as conn:
            row = conn.execute(
                "SELECT h.name, ST_Distance("
                "  h.geom::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography"
                ") / 1000.0, w.ae_4hr_pct, w.rtt_weeks "
                "FROM hospital h LEFT JOIN nhs_waiting w ON w.org_code = h.org_code "
                "ORDER BY h.geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326) LIMIT 1",
                [lng, lat, lng, lat],
            ).fetchone()
    except Exception:  # no DB, no hospitals, or PostGIS missing
        return None
    if not row:
        return None
    return {
        "hospital": row[0],
        "km": round(row[1], 1) if row[1] is not None else None,
        "ae4hr": row[2],
        "rttWeeks": row[3],
    }


def _map_png(geometry: dict | None, catchment_id: str) -> bytes | None:
    """An OSM basemap with the catchment drawn over it, for the export sidebar.

    Best effort: returns None if tiles cannot be fetched, and the renderer then
    falls back to the vector silhouette."""
    if not geometry:
        return None
    from .battlecard.staticmap_render import catchment_png

    lat, lng = _catchment_coord(catchment_id)
    return catchment_png(geometry, lat, lng)


def _brand_logo(catchment_id: str) -> bytes | None:
    """The brand logo bytes for the run, fetched from storage for embedding."""
    catchment = get_store().get_catchment(catchment_id)
    path = ((catchment or {}).get("input", {}).get("config") or {}).get("brandLogoPath")
    if not path:
        return None
    from . import assets

    return assets.fetch_logo(path)


@app.post("/catchments/{catchment_id}/shortlist/pdf")
def shortlist_pdf(
    catchment_id: str, request: ShortlistRequest, user: dict = Depends(current_user)
) -> Response:
    _require_access(catchment_id, user)
    cards = _shortlist_cards(catchment_id, request.area_codes)
    if not cards:
        raise HTTPException(status_code=404, detail="No battlecards for shortlist")
    pdf = render_battlecards_pdf(
        cards,
        _heading(catchment_id),
        logo=_brand_logo(catchment_id),
        accent=_brand_accent(catchment_id),
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="landlynk-shortlist.pdf"'
        },
    )


@app.post("/catchments/{catchment_id}/shortlist/pptx")
def shortlist_pptx(
    catchment_id: str, request: ShortlistRequest, user: dict = Depends(current_user)
) -> Response:
    _require_access(catchment_id, user)
    cards = _shortlist_cards(catchment_id, request.area_codes)
    if not cards:
        raise HTTPException(status_code=404, detail="No battlecards for shortlist")
    pptx = render_battlecards_pptx(
        cards,
        _heading(catchment_id),
        logo=_brand_logo(catchment_id),
        accent=_brand_accent(catchment_id),
    )
    return Response(
        content=pptx,
        media_type=(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ),
        headers={
            "Content-Disposition": 'attachment; filename="landlynk-shortlist.pptx"'
        },
    )


class CombineRequest(BaseModel):
    """Areas to merge into one aggregate Battlecard. Empty means the whole catchment."""

    area_codes: list[str] = []
    scope: str = "selection"  # "selection" or "whole"


def _combined_card(catchment_id: str, request: CombineRequest) -> Battlecard:
    from .battlecard.combine import build_combined_battlecard

    store = get_store()
    catchment = store.get_catchment(catchment_id)
    if catchment is None:
        raise HTTPException(status_code=404, detail="Catchment not found")
    areas = catchment.get("areas", [])
    names = {a["areaCode"]: a.get("name", a["areaCode"]) for a in areas}
    if request.scope == "whole" or not request.area_codes:
        codes = [a["areaCode"] for a in areas]
    else:
        codes = request.area_codes
    payloads = [
        p for c in codes if (p := store.get_battlecard(catchment_id, c)) is not None
    ]
    if not payloads:
        raise HTTPException(status_code=404, detail="No areas to combine")
    config = (catchment.get("input") or {}).get("config")
    # If a Local Area Profile was generated for this set with the default model,
    # bake it into the export so the deck carries the amenities.
    area_profile = None
    model = _default_model()
    if model:
        key = _area_profile_key(codes, model, _objective_id(catchment))
        area_profile = store.get_area_profile(key)
    return build_combined_battlecard(payloads, names, config, area_profile=area_profile)


@app.post("/catchments/{catchment_id}/combined/pdf")
def combined_pdf(
    catchment_id: str, request: CombineRequest, user: dict = Depends(current_user)
) -> Response:
    _require_access(catchment_id, user)
    card = _combined_card(catchment_id, request)
    return Response(
        content=render_battlecard_pdf(
            card,
            _heading(catchment_id),
            _catchment_geometry(catchment_id),
            _brand_logo(catchment_id),
            _brand_accent(catchment_id),
            _map_png(_catchment_geometry(catchment_id), catchment_id),
        ),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="landlynk-combined.pdf"'},
    )


@app.post("/catchments/{catchment_id}/report/pptx")
def report_pptx(
    catchment_id: str, request: CombineRequest, user: dict = Depends(current_user)
) -> Response:
    """Full multi-slide report deck for the selection or whole catchment."""
    _require_access(catchment_id, user)
    card = _combined_card(catchment_id, request)
    pptx = render_report_pptx(
        card,
        _heading(catchment_id),
        _brand_logo(catchment_id),
        _brand_accent(catchment_id),
        _brand_secondary(catchment_id),
        _map_png(_catchment_geometry(catchment_id), catchment_id),
        _development_context(catchment_id),
    )
    return Response(
        content=pptx,
        media_type=(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ),
        headers={"Content-Disposition": 'attachment; filename="landlynk-report.pptx"'},
    )


def _appraisal_verdict(card: Battlecard) -> dict:
    """A compact whole-catchment verdict for the housebuilder appraise and
    next-phase intents: does local income support the price, how deep is demand,
    and the addressable pool by segment. Derived from the combined card, so it
    uses the same reproducible engine as the Battlecard."""
    pr = card.pricing_rationale
    implied = pr.implied_affordable_price.value
    price_from = pr.price_from.value
    if implied is None or price_from is None:
        fit = "unknown"
    elif price_from <= implied:
        fit = "within"
    elif price_from <= implied * 1.2:
        fit = "stretch"
    else:
        fit = "above"
    seg = card.addressable_segments
    ks = card.visual_summary.key_statistics
    return {
        "priceFit": fit,
        "priceFrom": price_from,
        "impliedAffordablePrice": implied,
        "positioning": pr.positioning,
        "population": ks.population_catchment.value,
        "households": ks.households_catchment.value,
        "medianHousePrice": ks.median_house_price.value,
        "segments": {
            "firstTimeBuyer": seg.first_time_buyer_pipeline.value,
            "downsizer": seg.downsizer_pool.value,
            "family": seg.family_households.value,
        },
        "confidence": card.data_confidence.level,
    }


@app.get("/catchments/{catchment_id}/sites")
def catchment_sites(
    catchment_id: str, user: dict = Depends(current_user)
) -> dict:
    """Development sites (brownfield register) that fall inside the catchment.

    Best effort: returns an empty list without a database, the dataset or a
    catchment polygon, so the Find a site overlay degrades gracefully."""
    _require_access(catchment_id, user)
    geom = _catchment_geometry(catchment_id)
    if not geom:
        return {"sites": []}
    try:
        with get_pool().connection() as conn:
            rows = conn.execute(
                "SELECT s.reference, s.name, s.hectares, s.min_dwellings, "
                "s.max_dwellings, s.lat, s.lng, b.area_code, s.source_type "
                "FROM development_site s "
                "LEFT JOIN geo_boundaries b ON ST_Within(s.geom, b.geom) "
                "WHERE ST_Within(s.geom, ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)) "
                "ORDER BY s.max_dwellings DESC NULLS LAST LIMIT 1500",
                [json.dumps(geom)],
            ).fetchall()
    except Exception:  # no DB, no dataset, or PostGIS missing
        return {"sites": []}
    return {
        "sites": [
            {
                "reference": r[0],
                "name": r[1],
                "hectares": float(r[2]) if r[2] is not None else None,
                "minDwellings": r[3],
                "maxDwellings": r[4],
                "lat": float(r[5]),
                "lng": float(r[6]),
                "areaCode": r[7],
                "sourceType": r[8],
            }
            for r in rows
        ]
    }


@app.post("/catchments/{catchment_id}/verdict")
def catchment_verdict(
    catchment_id: str, request: CombineRequest, user: dict = Depends(current_user)
) -> dict:
    """Whole-catchment appraisal verdict (price fit and addressable demand)."""
    _require_access(catchment_id, user)
    verdict = _appraisal_verdict(_combined_card(catchment_id, request))
    # Whether the run carried an explicit target price. When it did not, the
    # price from is the engine default, so the UI must not present the price fit
    # as if the user chose that price.
    catchment = get_store().get_catchment(catchment_id)
    config = ((catchment or {}).get("input") or {}).get("config") or {}
    verdict["priceSet"] = bool((config.get("priceBand") or {}).get("from"))
    return verdict


@app.post("/catchments/{catchment_id}/combined/pptx")
def combined_pptx(
    catchment_id: str, request: CombineRequest, user: dict = Depends(current_user)
) -> Response:
    _require_access(catchment_id, user)
    card = _combined_card(catchment_id, request)
    return Response(
        content=render_battlecard_pptx(
            card,
            _heading(catchment_id),
            _catchment_geometry(catchment_id),
            _brand_logo(catchment_id),
            _brand_accent(catchment_id),
            _map_png(_catchment_geometry(catchment_id), catchment_id),
        ),
        media_type=(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ),
        headers={
            "Content-Disposition": 'attachment; filename="landlynk-combined.pptx"'
        },
    )


@app.get("/catchments/{catchment_id}/battlecards/{area_code}/pdf")
def get_battlecard_pdf(
    catchment_id: str, area_code: str, user: dict = Depends(current_user)
) -> Response:
    _require_access(catchment_id, user)
    data = get_store().get_battlecard(catchment_id, area_code)
    if data is None:
        raise HTTPException(status_code=404, detail="Battlecard not found")
    area_geom = _area_geometry(catchment_id, area_code)
    pdf = render_battlecard_pdf(
        Battlecard.model_validate(data),
        _heading(catchment_id),
        area_geom,
        _brand_logo(catchment_id),
        _brand_accent(catchment_id),
        _map_png(area_geom, catchment_id),
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="battlecard-{area_code}.pdf"'
        },
    )


@app.get("/catchments/{catchment_id}/battlecards/{area_code}/pptx")
def get_battlecard_pptx(
    catchment_id: str, area_code: str, user: dict = Depends(current_user)
) -> Response:
    _require_access(catchment_id, user)
    data = get_store().get_battlecard(catchment_id, area_code)
    if data is None:
        raise HTTPException(status_code=404, detail="Battlecard not found")
    area_geom = _area_geometry(catchment_id, area_code)
    pptx = render_battlecard_pptx(
        Battlecard.model_validate(data),
        _heading(catchment_id),
        area_geom,
        _brand_logo(catchment_id),
        _brand_accent(catchment_id),
        _map_png(area_geom, catchment_id),
    )
    return Response(
        content=pptx,
        media_type=(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="battlecard-{area_code}.pptx"'
        },
    )
