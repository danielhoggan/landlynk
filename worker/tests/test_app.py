"""Worker HTTP surface: health and the job lifecycle with a stubbed pipeline.

The real pipeline needs external services, so the run is monkeypatched to a fake
result. This verifies routing, status transitions and the response contracts the
web app consumes, without a database or network.
"""

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


@pytest.fixture
def client(monkeypatch):
    # Use the in-memory store and skip real dependency construction so the app
    # is exercised without a database or external services.
    from landlynk_worker.storage import InMemoryStore

    monkeypatch.setattr(app_module, "_store", InMemoryStore())
    monkeypatch.setattr(app_module, "get_deps", lambda: None)
    # No database in the unit tests; status falls back to the in-memory mirror.
    monkeypatch.setattr(app_module, "get_pool", lambda: None)
    # The default caller is bootstrapped as admin (sees all, can delete).
    monkeypatch.setattr(app_module.settings, "admin_emails", "tester@example.com")
    return TestClient(
        app_module.app,
        headers={"X-User-Email": "tester@example.com", "X-User-Name": "Tester"},
    )


def _user_headers(email: str) -> dict[str, str]:
    return {"X-User-Email": email, "X-User-Name": email.split("@")[0]}


def _fake_result() -> CatchmentResult:
    profile = AreaProfile(
        area_code="E02000001",
        area_type="MSOA",
        population=8000,
        households=3200,
        median_income=60000,
        mean_income=68000,
        median_age=39,
        tenure=TenureMix(0.25, 0.40, 0.10, 0.25),
        age=AgeProfile(0.18, 0.30, 0.28, 0.18, 0.06),
        family_household_share=0.55,
        proportion_inside=1.0,
    )
    config = ScoringConfig()
    score = compute_score(profile, config)
    card = assemble_battlecard(
        profile,
        config,
        score,
        rank=1,
        development=DevelopmentInfo(
            "Abbots Vale", "Stowmarket", "IP14 1AA", "s", [], []
        ),
        income_context=IncomeContext("A", 50000, "B", 70000),
    )
    return CatchmentResult(
        coordinate=Coordinate(lat=52.0, lng=1.0),
        isochrone={"type": "Polygon", "coordinates": []},
        areas=[
            ScoredArea("E02000001", "MSOA", "Area A", 1.0, score, 1),
        ],
        battlecards={"E02000001": card},
    )


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_job_lifecycle(client, monkeypatch):
    # Stub the orchestrator so the background task does not call external services.
    monkeypatch.setattr(app_module, "run_catchment", lambda **kwargs: _fake_result())

    submit = client.post(
        "/jobs/catchment",
        json={
            "kind": "postcode",
            "value": "IP14 1AA",
            "developmentName": "Abbots Vale",
        },
    )
    assert submit.status_code == 202
    job_id = submit.json()["id"]

    # TestClient runs background tasks synchronously, so the job is complete.
    catchment = client.get(f"/catchments/{job_id}").json()
    assert catchment["status"] == "complete"
    assert catchment["areas"][0]["areaCode"] == "E02000001"
    assert catchment["areas"][0]["rank"] == 1
    assert catchment["coordinate"] == {"lat": 52.0, "lng": 1.0}

    card = client.get(f"/catchments/{job_id}/battlecards/E02000001").json()
    assert card["areaCode"] == "E02000001"
    assert card["schemaVersion"]

    listing = client.get("/catchments").json()
    assert any(item["id"] == job_id for item in listing)
    entry = next(item for item in listing if item["id"] == job_id)
    assert entry["developmentName"] == "Abbots Vale"
    assert entry["areaCount"] == 1


def test_unknown_catchment_404(client):
    assert client.get("/catchments/does-not-exist").status_code == 404


def _submit(client, headers=None):
    return client.post(
        "/jobs/catchment",
        json={"kind": "postcode", "value": "IP14 1AA", "developmentName": "A"},
        headers=headers,
    ).json()["id"]


def test_history_is_private_then_shareable(client, monkeypatch):
    # Alice's run is invisible to Bob until she shares it, then it appears in
    # Bob's history flagged as shared.
    monkeypatch.setattr(app_module, "run_catchment", lambda **kwargs: _fake_result())
    alice, bob = _user_headers("alice@x.com"), _user_headers("bob@x.com")

    job_id = _submit(client, alice)
    assert any(
        c["id"] == job_id for c in client.get("/catchments", headers=alice).json()
    )
    assert not any(
        c["id"] == job_id for c in client.get("/catchments", headers=bob).json()
    )

    # Only the owner (or an admin) can share.
    assert (
        client.post(
            f"/catchments/{job_id}/shares", json={"emails": ["bob@x.com"]}, headers=bob
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/catchments/{job_id}/shares",
            json={"emails": ["bob@x.com"]},
            headers=alice,
        ).status_code
        == 204
    )
    bob_list = client.get("/catchments", headers=bob).json()
    shared = next(c for c in bob_list if c["id"] == job_id)
    assert shared["shared"] is True


def test_opening_a_run_requires_access(client, monkeypatch):
    # Sharing is in-portal: a non-owner cannot open another user's run by id,
    # but can once it is shared with them.
    monkeypatch.setattr(app_module, "run_catchment", lambda **kwargs: _fake_result())
    alice, bob = _user_headers("alice@x.com"), _user_headers("bob@x.com")
    job_id = _submit(client, alice)

    assert client.get(f"/catchments/{job_id}", headers=alice).status_code == 200
    assert client.get(f"/catchments/{job_id}", headers=bob).status_code == 403
    assert (
        client.get(
            f"/catchments/{job_id}/battlecards/E02000001", headers=bob
        ).status_code
        == 403
    )

    client.post(
        f"/catchments/{job_id}/shares", json={"emails": ["bob@x.com"]}, headers=alice
    )
    assert client.get(f"/catchments/{job_id}", headers=bob).status_code == 200
    # Admins can open anything.
    assert client.get(f"/catchments/{job_id}").status_code == 200


def test_archive_hides_from_default_history(client, monkeypatch):
    monkeypatch.setattr(app_module, "run_catchment", lambda **kwargs: _fake_result())
    alice = _user_headers("alice@x.com")
    job_id = _submit(client, alice)

    assert (
        client.post(f"/catchments/{job_id}/archive", headers=alice).status_code == 204
    )
    assert not any(
        c["id"] == job_id for c in client.get("/catchments", headers=alice).json()
    )
    archived = client.get("/catchments?archived=true", headers=alice).json()
    assert any(c["id"] == job_id for c in archived)


def test_only_admin_deletes(client, monkeypatch):
    monkeypatch.setattr(app_module, "run_catchment", lambda **kwargs: _fake_result())
    alice = _user_headers("alice@x.com")
    job_id = _submit(client, alice)
    # The owner is a plain user; delete is admin only.
    assert client.delete(f"/catchments/{job_id}", headers=alice).status_code == 403
    # The default fixture caller is an admin.
    assert client.delete(f"/catchments/{job_id}").status_code == 204


def test_roles_and_user_directory(client):
    alice = _user_headers("alice@x.com")
    # A normal user cannot list users or change roles.
    assert client.get("/admin/users", headers=alice).status_code == 403
    # The admin can, and promoting another user works.
    client.get("/me", headers=alice)  # ensure alice exists in the directory
    assert client.get("/admin/users").status_code == 200
    assert (
        client.put("/admin/users/alice@x.com/role", json={"role": "admin"}).status_code
        == 204
    )
    assert client.get("/me", headers=alice).json()["role"] == "admin"


def test_account_settings_roundtrip(client):
    alice = _user_headers("alice@x.com")
    client.get("/me", headers=alice)  # upsert the user first (settings FK)
    assert client.get("/me/settings", headers=alice).json()["settings"] is None
    body = {"settings": {"affordabilityMultiple": 5.0, "enableLA": True}}
    assert client.put("/me/settings", json=body, headers=alice).status_code == 204
    assert (
        client.get("/me/settings", headers=alice).json()["settings"] == body["settings"]
    )


def test_shortlist_export(client, monkeypatch):
    # Star one area and combine into one PDF and one PPTX through the shortlist
    # endpoints, the combined-export path a builder uses for a multi-area pitch.
    monkeypatch.setattr(app_module, "run_catchment", lambda **kwargs: _fake_result())
    job_id = client.post(
        "/jobs/catchment",
        json={"kind": "postcode", "value": "IP14 1AA", "developmentName": "A"},
    ).json()["id"]

    pdf = client.post(
        f"/catchments/{job_id}/shortlist/pdf", json={"area_codes": ["E02000001"]}
    )
    assert pdf.status_code == 200
    assert pdf.content[:5] == b"%PDF-"

    pptx = client.post(
        f"/catchments/{job_id}/shortlist/pptx", json={"area_codes": ["E02000001"]}
    )
    assert pptx.status_code == 200
    assert pptx.content[:2] == b"PK"


def test_shortlist_export_empty_selection_404(client, monkeypatch):
    monkeypatch.setattr(app_module, "run_catchment", lambda **kwargs: _fake_result())
    job_id = client.post(
        "/jobs/catchment",
        json={"kind": "postcode", "value": "IP14 1AA", "developmentName": "A"},
    ).json()["id"]
    # Codes that do not resolve to a stored battlecard yield no document.
    res = client.post(
        f"/catchments/{job_id}/shortlist/pdf", json={"area_codes": ["E02999999"]}
    )
    assert res.status_code == 404


def test_delete_catchment(client, monkeypatch):
    monkeypatch.setattr(app_module, "run_catchment", lambda **kwargs: _fake_result())
    job_id = client.post(
        "/jobs/catchment",
        json={"kind": "postcode", "value": "IP14 1AA", "developmentName": "A"},
    ).json()["id"]
    assert client.get(f"/catchments/{job_id}").status_code == 200
    assert client.delete(f"/catchments/{job_id}").status_code == 204
    assert client.get(f"/catchments/{job_id}").status_code == 404
    assert client.delete(f"/catchments/{job_id}").status_code == 404


def test_reference_load_dispatch(client, monkeypatch):
    # Avoid building a real pool or running a real load.
    monkeypatch.setattr(app_module, "get_pool", lambda: object())
    calls = {}
    monkeypatch.setattr(
        app_module.refdata,
        "run_load",
        lambda pool, dataset, params: calls.update(dataset=dataset, params=params),
    )
    res = client.post(
        "/admin/reference/geo_boundaries",
        json={"url": "https://x/FeatureServer/0/query", "areaType": "MSOA"},
    )
    assert res.status_code == 202
    assert calls["dataset"] == "geo_boundaries"
    assert calls["params"]["url"].endswith("/query")


def test_reference_load_unknown_dataset(client):
    assert client.post("/admin/reference/nope", json={}).status_code == 404


def test_reference_status_ok(client):
    assert client.get("/admin/reference/status").status_code == 200
