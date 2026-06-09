"""Builder profiles: org CRUD and external-user scoping."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from landlynk_worker import app as app_module
from landlynk_worker.storage import InMemoryStore


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
