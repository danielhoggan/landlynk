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

import logging
import uuid
from typing import TYPE_CHECKING

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Response
from pydantic import BaseModel, Field

from . import refdata
from .api_models import CatchmentJobRequest, to_development_info, to_scoring_config
from .battlecard import (
    Battlecard,
    render_battlecard_pdf,
    render_battlecard_pptx,
    render_battlecards_pdf,
    render_battlecards_pptx,
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
def list_segments_endpoint() -> list[dict]:
    """The predefined audience segments for segment-first targeting."""
    from .scoring.segments import list_segments

    return list_segments()


def _check_admin(token: str | None) -> None:
    if settings.admin_token and token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")


def current_user(
    x_user_email: str | None = Header(default=None),
    x_user_name: str | None = Header(default=None),
) -> dict:
    """Resolve the caller from the SSO-gated web layer's forwarded headers.

    The web service authenticates via Azure AD and forwards the signed-in
    identity. The worker is private, so it trusts these headers. Each call
    upserts the user, applying the admin bootstrap from settings.admin_emails.
    """
    if not x_user_email:
        return {"email": None, "name": None, "role": "internal-user"}
    email = x_user_email.strip().lower()
    admin = email in settings.admin_email_set()
    try:
        return get_store().upsert_user(email, x_user_name, admin)
    except Exception:  # never block a request on the user directory
        _log.exception("upsert_user failed for %s", email)
        return {
            "email": email,
            "name": x_user_name,
            "role": "admin" if admin else "internal-user",
        }


def _require_admin(user: dict) -> None:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")


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


@app.post("/jobs/catchment", status_code=202)
def submit_catchment_job(
    request: CatchmentJobRequest,
    background: BackgroundTasks,
    user: dict = Depends(current_user),
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
        created_by=user.get("email") or "system",
    )
    background.add_task(_run_job, job_id, request, config)
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
    return user


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


def _scope_group(user: dict) -> str | None:
    """The group a user is restricted to, or None to see all profiles.

    Admins and internal users are unscoped. An external user pinned to a group
    sees only that group's brands and profiles.
    """
    if user.get("role") == "admin":
        return None
    return user.get("builderGroupId")


@app.get("/builders/profiles")
def list_profiles(user: dict = Depends(current_user)) -> list[dict]:
    """Targeting profiles the caller may use, scoped to their group if external."""
    return get_store().list_builder_profiles(_scope_group(user))


class GroupRequest(BaseModel):
    name: str


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
    get_store().create_builder_group(group_id, request.name)
    return {"id": group_id, "name": request.name}


@app.delete("/admin/builders/groups/{group_id}", status_code=204)
def admin_delete_group(group_id: str, user: dict = Depends(current_user)) -> Response:
    _require_admin(user)
    get_store().delete_builder_group(group_id)
    return Response(status_code=204)


class BuilderRequest(BaseModel):
    group_id: str = Field(alias="groupId")
    name: str
    theme_heading: str = Field(default="#4169E1", alias="themeHeading")

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
        builder_id, request.group_id, request.name, request.theme_heading
    )
    return {"id": builder_id}


@app.delete("/admin/builders/{builder_id}", status_code=204)
def admin_delete_builder(
    builder_id: str, user: dict = Depends(current_user)
) -> Response:
    _require_admin(user)
    get_store().delete_builder(builder_id)
    return Response(status_code=204)


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
    return {"id": profile["id"]}


@app.delete("/admin/builders/profiles/{profile_id}", status_code=204)
def admin_delete_profile(
    profile_id: str, user: dict = Depends(current_user)
) -> Response:
    _require_admin(user)
    get_store().delete_builder_profile(profile_id)
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
    import hashlib

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

    key_src = "|".join(sorted(codes)) + "::" + model
    cache_key = hashlib.sha256(key_src.encode()).hexdigest()
    if not request.refresh:
        cached = store.get_area_profile(cache_key)
        if cached is not None:
            return {**cached, "cached": True}

    names = [by_code[c] for c in codes]
    try:
        payload = generate_area_profile(names, model)
    except Exception as exc:
        _log.exception("Area profile generation failed")
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    store.save_area_profile(cache_key, model, payload)
    return {"model": model, **payload, "cached": False}


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


@app.post("/catchments/{catchment_id}/shortlist/pdf")
def shortlist_pdf(
    catchment_id: str, request: ShortlistRequest, user: dict = Depends(current_user)
) -> Response:
    _require_access(catchment_id, user)
    cards = _shortlist_cards(catchment_id, request.area_codes)
    if not cards:
        raise HTTPException(status_code=404, detail="No battlecards for shortlist")
    pdf = render_battlecards_pdf(cards, _heading(catchment_id))
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
    pptx = render_battlecards_pptx(cards, _heading(catchment_id))
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
        import hashlib

        key = hashlib.sha256(("|".join(sorted(codes)) + "::" + model).encode())
        area_profile = store.get_area_profile(key.hexdigest())
    return build_combined_battlecard(payloads, names, config, area_profile=area_profile)


@app.post("/catchments/{catchment_id}/combined/pdf")
def combined_pdf(
    catchment_id: str, request: CombineRequest, user: dict = Depends(current_user)
) -> Response:
    _require_access(catchment_id, user)
    card = _combined_card(catchment_id, request)
    return Response(
        content=render_battlecard_pdf(card, _heading(catchment_id)),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="landlynk-combined.pdf"'},
    )


@app.post("/catchments/{catchment_id}/combined/pptx")
def combined_pptx(
    catchment_id: str, request: CombineRequest, user: dict = Depends(current_user)
) -> Response:
    _require_access(catchment_id, user)
    card = _combined_card(catchment_id, request)
    return Response(
        content=render_battlecard_pptx(card, _heading(catchment_id)),
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
    pdf = render_battlecard_pdf(Battlecard.model_validate(data), _heading(catchment_id))
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
    pptx = render_battlecard_pptx(
        Battlecard.model_validate(data), _heading(catchment_id)
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
