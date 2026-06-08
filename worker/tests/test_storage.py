"""InMemoryStore serialises catchments and Battlecards to the web contract."""

from __future__ import annotations

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
from landlynk_worker.storage import InMemoryStore, JobInput


def _result() -> tuple[CatchmentResult, ScoringConfig]:
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
        proportion_inside=0.9,
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
    result = CatchmentResult(
        coordinate=Coordinate(lat=52.0, lng=1.0),
        isochrone={"type": "Polygon", "coordinates": []},
        areas=[
            ScoredArea(
                "E02000001", "MSOA", "Area A", 0.9, score, 1, {"type": "Polygon"}
            )
        ],
        battlecards={"E02000001": card},
    )
    return result, config


def test_create_and_read_lifecycle():
    store = InMemoryStore()
    job = JobInput(kind="postcode", value="IP14 1AA", development_name="Abbots Vale")
    store.create_job("cid", job, ScoringConfig(), "system")

    queued = store.get_catchment("cid")
    assert queued["status"] == "queued"
    assert queued["areas"] == []
    assert queued["input"]["developmentName"] == "Abbots Vale"

    result, config = _result()
    store.save_result("cid", result, config)

    done = store.get_catchment("cid")
    assert done["status"] == "complete"
    assert done["coordinate"] == {"lat": 52.0, "lng": 1.0}
    assert done["areas"][0]["areaCode"] == "E02000001"
    assert done["areas"][0]["band"] in {"high", "mid", "low"}
    assert done["areas"][0]["geometry"] == {"type": "Polygon"}


def test_get_battlecard_round_trips_payload():
    store = InMemoryStore()
    store.create_job(
        "cid",
        JobInput("postcode", "IP14 1AA", "Abbots Vale"),
        ScoringConfig(),
        "system",
    )
    result, config = _result()
    store.save_result("cid", result, config)

    card = store.get_battlecard("cid", "E02000001")
    assert card["areaCode"] == "E02000001"
    assert card["schemaVersion"]


def test_missing_catchment_returns_none():
    store = InMemoryStore()
    assert store.get_catchment("nope") is None
    assert store.get_battlecard("nope", "X") is None


def test_delete_catchment():
    store = InMemoryStore()
    store.create_job("cid", JobInput("postcode", "X", "Y"), ScoringConfig(), "system")
    assert store.delete_catchment("cid") is True
    assert store.get_catchment("cid") is None
    assert store.delete_catchment("cid") is False  # already gone


def test_mark_status_failure():
    store = InMemoryStore()
    store.create_job("cid", JobInput("postcode", "X", "Y"), ScoringConfig(), "system")
    store.mark_status("cid", "failed", "boom")
    cat = store.get_catchment("cid")
    assert cat["status"] == "failed"
    assert cat["error"] == "boom"
