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
    return TestClient(app_module.app)


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
