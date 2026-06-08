"""Integration test against a real PostGIS, complementing the offline units.

Skipped unless WORKER_TEST_DATABASE_URL points at a PostGIS database (for CI or
local). It applies the migrations then round-trips a catchment through
PostgresStore, exercising the geometry writes and reads that the in-memory store
cannot cover.
"""

from __future__ import annotations

import os
import uuid

import pytest

DB_URL = os.environ.get("WORKER_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DB_URL,
    reason="set WORKER_TEST_DATABASE_URL to run the PostGIS integration test",
)


@pytest.fixture(scope="module")
def pool():
    from psycopg_pool import ConnectionPool

    from landlynk_worker import migrate

    migrate.run(DB_URL)  # ensure schema + PostGIS
    p = ConnectionPool(DB_URL, min_size=1, max_size=4)
    yield p
    p.close()


def _result():
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
    poly = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]],
    }
    result = CatchmentResult(
        coordinate=Coordinate(lat=52.0, lng=1.0),
        isochrone=poly,
        areas=[ScoredArea("E02000001", "MSOA", "Area A", 0.9, score, 1, poly)],
        battlecards={"E02000001": card},
    )
    return result, config


def test_postgres_store_round_trip(pool):
    from landlynk_worker.storage import JobInput, PostgresStore

    store = PostgresStore(pool)
    cid = str(uuid.uuid4())
    store.create_job(
        cid, JobInput("postcode", "IP14 1AA", "Abbots Vale"), _result()[1], "tester"
    )
    result, config = _result()
    store.save_result(cid, result, config)

    catchment = store.get_catchment(cid)
    assert catchment["status"] == "complete"
    assert catchment["coordinate"]["lat"] == pytest.approx(52.0, abs=1e-6)
    assert catchment["areas"][0]["areaCode"] == "E02000001"

    card = store.get_battlecard(cid, "E02000001")
    assert card["areaCode"] == "E02000001"

    listing = store.list_catchments()
    assert any(item["id"] == cid for item in listing)
