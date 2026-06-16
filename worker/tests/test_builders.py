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
    monkeypatch.setattr(app_module.settings, "planit_enabled", False)
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


def test_me_brands_from_group_grant_and_brand_grants(client):
    # A whole-group grant exposes all the group's brands; the active brand is the
    # user's choice, so /me just lists the accessible brands (sorted by name).
    g = client.post("/admin/builders/groups", json={"name": "Plc"}).json()["id"]
    alpha = client.post(
        "/admin/builders",
        json={"groupId": g, "name": "Alpha", "themeAccent": "#111111"},
    ).json()["id"]
    client.post(
        "/admin/builders",
        json={"groupId": g, "name": "Zeta", "themeAccent": "#222222"},
    ).json()["id"]

    client.post(
        "/jobs/catchment",
        json={"kind": "postcode", "value": "X", "developmentName": "D"},
        headers=_h("ext@x.com"),
    )
    # No grant: no brands.
    assert client.get("/me", headers=_h("ext@x.com")).json()["brands"] == []

    # Whole-group grant: both brands, sorted by name.
    client.put("/admin/users/ext@x.com/group", json={"groupId": g})
    brands = client.get("/me", headers=_h("ext@x.com")).json()["brands"]
    assert [b["name"] for b in brands] == ["Alpha", "Zeta"]
    assert brands[0]["builderId"] == alpha
    assert brands[0]["companyName"] == "Plc"


def test_specific_brand_grant_across_groups(client):
    # An agency user assigned specific brands sees only those, across groups.
    g1 = client.post("/admin/builders/groups", json={"name": "Tilia"}).json()["id"]
    g2 = client.post("/admin/builders/groups", json={"name": "Hopkins"}).json()["id"]
    b1 = client.post(
        "/admin/builders", json={"groupId": g1, "name": "Tilia Homes"}
    ).json()["id"]
    b2 = client.post(
        "/admin/builders", json={"groupId": g2, "name": "Hopkins Homes"}
    ).json()["id"]
    client.post(
        "/admin/builders", json={"groupId": g2, "name": "Other Brand"}
    ).json()["id"]

    client.post(
        "/jobs/catchment",
        json={"kind": "postcode", "value": "X", "developmentName": "D"},
        headers=_h("cmo@x.com"),
    )
    client.put("/admin/users/cmo@x.com/brands", json={"brandIds": [b1, b2]})
    brands = client.get("/me", headers=_h("cmo@x.com")).json()["brands"]
    assert {b["name"] for b in brands} == {"Tilia Homes", "Hopkins Homes"}
    assert client.get("/admin/users/cmo@x.com/brands").json()["brandIds"] == sorted(
        [b1, b2]
    )


def test_specific_brand_grant_overrides_group_grant(client):
    # Assigning a specific brand restricts the user to exactly that brand, even
    # when they also hold a whole-group grant.
    g = client.post("/admin/builders/groups", json={"name": "Plc"}).json()["id"]
    a = client.post(
        "/admin/builders", json={"groupId": g, "name": "Aone"}
    ).json()["id"]
    client.post("/admin/builders", json={"groupId": g, "name": "Btwo"})
    client.post(
        "/jobs/catchment",
        json={"kind": "postcode", "value": "X", "developmentName": "D"},
        headers=_h("ext@x.com"),
    )
    client.put("/admin/users/ext@x.com/group", json={"groupId": g})
    assert len(client.get("/me", headers=_h("ext@x.com")).json()["brands"]) == 2

    client.put("/admin/users/ext@x.com/brands", json={"brandIds": [a]})
    brands = client.get("/me", headers=_h("ext@x.com")).json()["brands"]
    assert [b["builderId"] for b in brands] == [a]


def test_update_brand_palette(client):
    g = client.post("/admin/builders/groups", json={"name": "Plc"}).json()["id"]
    b = client.post(
        "/admin/builders",
        json={"groupId": g, "name": "Aone", "themeAccent": "#111111"},
    ).json()["id"]
    assert (
        client.put(
            f"/admin/builders/{b}",
            json={"themeAccent": "#C9A24B", "industry": "retail"},
        ).status_code
        == 204
    )
    row = next(x for x in client.get(f"/admin/builders?group_id={g}").json())
    assert row["themeAccent"] == "#C9A24B" and row["industry"] == "retail"
    assert client.put("/admin/builders/nope", json={"name": "x"}).status_code == 404


def test_brand_industry_and_usage_scoped_to_active_brand(client):
    # Industry lives on the brand; the active brand scopes the AI allowance.
    g = client.post(
        "/admin/builders/groups", json={"name": "Acme", "monthlyCap": 5}
    ).json()["id"]
    b = client.post(
        "/admin/builders",
        json={"groupId": g, "name": "Acme Retail", "industry": "retail"},
    ).json()["id"]
    client.post(
        "/jobs/catchment",
        json={"kind": "postcode", "value": "X", "developmentName": "D"},
        headers=_h("ext@x.com"),
    )
    client.put("/admin/users/ext@x.com/brands", json={"brandIds": [b]})

    brand = client.get("/me", headers=_h("ext@x.com")).json()["brands"][0]
    assert brand["industry"] == "retail" and brand["companyName"] == "Acme"

    # With the brand active, usage is metered to that brand's group cap.
    usage = client.get(
        "/builders/usage",
        headers={**_h("ext@x.com"), "X-Active-Brand": b},
    ).json()
    assert usage["metered"] is True and usage["cap"] == 5
    assert usage["resetsOn"].endswith("-01")


def test_job_run_allowance_meters_and_blocks(client, monkeypatch):
    # A monthly run cap, pooled per group like the AI cap, blocks once spent.
    monkeypatch.setattr(app_module, "run_catchment", lambda **kwargs: _fake_result())
    g = client.post(
        "/admin/builders/groups", json={"name": "Plc", "monthlyJobCap": 2}
    ).json()["id"]
    ext = _h("ext@x.com")
    client.get("/me", headers=ext)  # create the user record before granting access
    client.put("/admin/users/ext@x.com/group", json={"groupId": g})
    client.put("/admin/users/ext@x.com/role", json={"role": "external-user"})
    body = {"kind": "postcode", "value": "NN15 7FJ", "developmentName": "Westhill"}

    usage = client.get("/builders/usage", headers=ext).json()["jobs"]
    assert usage["metered"] is True and usage["cap"] == 2 and usage["used"] == 0
    assert usage["resetsOn"].endswith("-01")

    assert client.post("/jobs/catchment", json=body, headers=ext).status_code == 202
    assert client.post("/jobs/catchment", json=body, headers=ext).status_code == 202
    # Cap reached: the next run is refused.
    assert client.post("/jobs/catchment", json=body, headers=ext).status_code == 429

    usage = client.get("/builders/usage", headers=ext).json()["jobs"]
    assert usage["used"] == 2 and usage["remaining"] == 0


def test_job_runs_survive_catchment_deletion(client, monkeypatch):
    # Deleting or archiving a catchment must not give back a spent run.
    monkeypatch.setattr(app_module, "run_catchment", lambda **kwargs: _fake_result())
    g = client.post(
        "/admin/builders/groups", json={"name": "Plc", "monthlyJobCap": 5}
    ).json()["id"]
    ext = _h("ext@x.com")
    client.get("/me", headers=ext)  # create the user record before granting access
    client.put("/admin/users/ext@x.com/group", json={"groupId": g})
    client.put("/admin/users/ext@x.com/role", json={"role": "external-user"})
    body = {"kind": "postcode", "value": "NN15 7FJ", "developmentName": "Westhill"}
    job_id = client.post("/jobs/catchment", json=body, headers=ext).json()["id"]

    assert client.delete(f"/catchments/{job_id}").status_code == 204
    usage = client.get("/builders/usage", headers=ext).json()["jobs"]
    assert usage["used"] == 1 and usage["remaining"] == 4


def test_admin_is_unmetered_for_runs(client):
    # Even with a zero cap on a group, an admin caller is never blocked.
    client.post("/admin/builders/groups", json={"name": "Plc", "monthlyJobCap": 0})
    usage = client.get("/builders/usage").json()["jobs"]
    assert usage["metered"] is False
    body = {"kind": "postcode", "value": "NN15 7FJ", "developmentName": "Westhill"}
    assert client.post("/jobs/catchment", json=body).status_code == 202


def test_catchment_verdict(client, monkeypatch):
    # The appraise/next-phase verdict: a price fit and addressable demand for the
    # whole catchment, derived from the combined card.
    monkeypatch.setattr(app_module, "run_catchment", lambda **kwargs: _fake_result())
    job = client.post(
        "/jobs/catchment",
        json={
            "kind": "postcode",
            "value": "IP1 1AA",
            "developmentName": "D",
            "config": {"priceBand": {"from": 250000, "to": 400000}},
        },
    ).json()["id"]
    v = client.post(f"/catchments/{job}/verdict", json={"scope": "whole"})
    assert v.status_code == 200
    body = v.json()
    assert body["priceFit"] in {"within", "stretch", "above", "unknown"}
    assert "firstTimeBuyer" in body["segments"]
    assert body["confidence"] in {"high", "medium", "low"}


def test_cached_area_profile_is_read_only(client, monkeypatch):
    # GET returns a snapshot only after one is generated, and never generates
    # itself (so a historic run can auto-show without spending the allowance).
    monkeypatch.setattr(app_module, "run_catchment", lambda **kwargs: _fake_result())
    ext = _h("ext@x.com")
    job = client.post(
        "/jobs/catchment",
        json={"kind": "postcode", "value": "IP1 1AA", "developmentName": "D"},
        headers=ext,
    ).json()["id"]

    monkeypatch.setattr(app_module.settings, "openai_api_key", "sk-test")
    client.put("/admin/models/default", json={"model": "gpt-4o"})
    monkeypatch.setattr(
        "landlynk_worker.enrichment.generate_area_profile",
        lambda names, model, transport=None: {"description": "x", "amenities": []},
    )

    # Nothing cached: the read-only GET reports no profile and does not generate.
    assert (
        client.get(f"/catchments/{job}/area-profile", headers=ext).json()["profile"]
        is None
    )

    # Generate once, then the GET serves the cached snapshot.
    gen = client.post(
        f"/catchments/{job}/area-profile", json={"scope": "whole"}, headers=ext
    )
    assert gen.status_code == 200 and gen.json()["cached"] is False
    got = client.get(f"/catchments/{job}/area-profile", headers=ext).json()["profile"]
    assert got is not None and got["cached"] is True and got["description"] == "x"


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
