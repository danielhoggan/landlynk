"""Builder profiles: org CRUD and external-user scoping."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from landlynk_worker import app as app_module
from landlynk_worker.battlecard import (
    DevelopmentInfo,
    IncomeContext,
    assemble_battlecard,
)
from landlynk_worker.pipeline.orchestrate import CatchmentResult, ScoredArea
from landlynk_worker.pipeline.resolve import Coordinate
from landlynk_worker.scoring import (
    AgeProfile,
    AreaProfile,
    ScoringConfig,
    TenureMix,
    compute_score,
)
from landlynk_worker.storage import InMemoryStore


def _fake_result() -> CatchmentResult:
    profile = AreaProfile(
        "E02000001",
        "MSOA",
        8000,
        3200,
        60000,
        68000,
        39,
        TenureMix(0.25, 0.40, 0.10, 0.25),
        AgeProfile(0.18, 0.30, 0.28, 0.18, 0.06),
        0.55,
        1.0,
    )
    score = compute_score(profile, ScoringConfig())
    card = assemble_battlecard(
        profile,
        ScoringConfig(),
        score,
        rank=1,
        development=DevelopmentInfo("D", "Town", "IP1 1AA", "s", [], []),
        income_context=IncomeContext("A", 50000, "B", 70000),
    )
    return CatchmentResult(
        coordinate=Coordinate(lat=52.0, lng=1.0),
        isochrone={"type": "Polygon", "coordinates": []},
        areas=[ScoredArea("E02000001", "MSOA", "Area A", 1.0, score, 1)],
        battlecards={"E02000001": card},
    )


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, "_store", InMemoryStore())
    monkeypatch.setattr(app_module, "get_pool", lambda: None)
    monkeypatch.setattr(app_module.settings, "admin_emails", "admin@x.com")
    return TestClient(
        app_module.app,
        headers={"X-User-Email": "admin@x.com", "X-User-Name": "Admin"},
    )


def _h(email):
    return {"X-User-Email": email, "X-User-Name": email.split("@")[0]}


def test_builder_profile_crud_and_scoping(client):
    # Admin builds two groups, each with a brand and a profile.
    g1 = client.post("/admin/builders/groups", json={"name": "Bellway plc"}).json()[
        "id"
    ]
    g2 = client.post("/admin/builders/groups", json={"name": "Hopkins"}).json()["id"]
    b1 = client.post(
        "/admin/builders",
        json={"groupId": g1, "name": "Bellway", "themeHeading": "#0A1F44"},
    ).json()["id"]
    b2 = client.post(
        "/admin/builders", json={"groupId": g2, "name": "Hopkins Homes"}
    ).json()["id"]
    client.post(
        "/admin/builders/profiles",
        json={
            "builderId": b1,
            "name": "FTB product",
            "segment": "first_time_buyer",
            "bedRange": "2 to 3",
        },
    )
    client.post(
        "/admin/builders/profiles",
        json={"builderId": b2, "name": "Family", "segment": "growing_family"},
    )

    # Admin sees all profiles.
    all_profiles = client.get("/builders/profiles").json()
    assert len(all_profiles) == 2
    assert {p["groupName"] for p in all_profiles} == {"Bellway plc", "Hopkins"}
    assert any(p["themeHeading"] == "#0A1F44" for p in all_profiles)

    # An external user pinned to group 1 sees only group 1's profile.
    client.post(
        "/jobs/catchment",
        json={"kind": "postcode", "value": "X", "developmentName": "D"},
        headers=_h("ext@x.com"),
    )
    client.put("/admin/users/ext@x.com/group", json={"groupId": g1})
    client.put("/admin/users/ext@x.com/role", json={"role": "external-user"})
    scoped = client.get("/builders/profiles", headers=_h("ext@x.com")).json()
    assert len(scoped) == 1
    assert scoped[0]["groupId"] == g1


def test_non_admin_cannot_manage_builders(client):
    assert (
        client.get("/admin/builders/groups", headers=_h("u@x.com")).status_code == 403
    )
    assert (
        client.post(
            "/admin/builders/groups", json={"name": "X"}, headers=_h("u@x.com")
        ).status_code
        == 403
    )


def test_external_user_llm_cap_enforced(client, monkeypatch):
    # A group with a cap of 1: the external user gets one generation, then 429.
    monkeypatch.setattr(app_module, "run_catchment", lambda **kwargs: _fake_result())
    g = client.post(
        "/admin/builders/groups", json={"name": "Capped", "monthlyCap": 1}
    ).json()["id"]
    ext = _h("ext@x.com")
    # ext owns the catchment so they may open it; admin then scopes them.
    job = client.post(
        "/jobs/catchment",
        json={"kind": "postcode", "value": "IP1 1AA", "developmentName": "D"},
        headers=ext,
    ).json()["id"]
    client.put("/admin/users/ext@x.com/role", json={"role": "external-user"})
    client.put("/admin/users/ext@x.com/group", json={"groupId": g})

    monkeypatch.setattr(app_module.settings, "openai_api_key", "sk-test")
    client.put("/admin/models/default", json={"model": "gpt-4o"})
    monkeypatch.setattr(
        "landlynk_worker.enrichment.generate_area_profile",
        lambda names, model, transport=None: {"description": "x", "amenities": []},
    )

    usage = client.get("/builders/usage", headers=ext).json()
    assert usage["metered"] is True and usage["cap"] == 1

    first = client.post(
        f"/catchments/{job}/area-profile", json={"scope": "whole"}, headers=ext
    )
    assert first.status_code == 200
    # Second generation (force refresh to skip cache) exceeds the cap.
    second = client.post(
        f"/catchments/{job}/area-profile",
        json={"scope": "whole", "refresh": True},
        headers=ext,
    )
    assert second.status_code == 429
