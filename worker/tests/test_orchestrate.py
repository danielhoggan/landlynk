"""End to end pipeline orchestration with injected fakes.

Proves the stages compose: resolve, isochrone, intersect, join, score, assemble,
producing ranked areas and a valid Battlecard each, with no network or database.
"""

from __future__ import annotations

from landlynk_worker.battlecard import DevelopmentInfo
from landlynk_worker.battlecard.schema import Battlecard
from landlynk_worker.pipeline.intersect import area_geometry_from_geojson
from landlynk_worker.pipeline.isochrone import InMemoryIsochroneCache
from landlynk_worker.pipeline.orchestrate import PipelineDeps, run_catchment
from landlynk_worker.pipeline.reference import AreaReference
from landlynk_worker.pipeline.resolve import Coordinate
from landlynk_worker.scoring import AgeProfile, AreaProfile, ScoringConfig, TenureMix

# A large isochrone polygon covering both fixture areas.
ISOCHRONE = {
    "type": "Polygon",
    "coordinates": [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]],
}


def _box(code: str, x0, y0, x1, y1) -> object:
    return area_geometry_from_geojson(
        code,
        "MSOA",
        {
            "type": "Polygon",
            "coordinates": [[[x0, y0], [x0, y1], [x1, y1], [x1, y0], [x0, y0]]],
        },
    )


def _profile(code: str, median_income: float, proportion: float) -> AreaProfile:
    return AreaProfile(
        area_code=code,
        area_type="MSOA",
        population=8000,
        households=3200,
        median_income=median_income,
        mean_income=median_income + 6000,
        median_age=40,
        tenure=TenureMix(
            owns_outright=0.25,
            owns_with_mortgage=0.40,
            social_rented=0.10,
            private_rented=0.25,
        ),
        age=AgeProfile(
            age_0_15=0.18,
            age_16_34=0.30,
            age_35_54=0.28,
            age_55_74=0.18,
            age_75_plus=0.06,
        ),
        family_household_share=0.55,
        proportion_inside=proportion,
    )


class FakeReference:
    """Two areas: a well-aligned one and a far-too-rich one."""

    def candidate_area_geometries(self, isochrone, area_type):
        return [
            _box("ALIGNED", 0, 0, 5, 5),  # fully inside
            _box("RICH", 5, 0, 15, 5),  # half inside
        ]

    def area_reference(self, area_code, area_type, proportion_inside):
        target = 72_000  # midpoint(250k,400k)/4.5
        income = target if area_code == "ALIGNED" else 250_000
        name = "Aligned Area" if area_code == "ALIGNED" else "Rich Area"
        return AreaReference(
            profile=_profile(area_code, income, proportion_inside), name=name
        )


class StaticProvider:
    def __init__(self) -> None:
        self.calls = 0

    def fetch(self, params):
        self.calls += 1
        return ISOCHRONE


def _development() -> DevelopmentInfo:
    return DevelopmentInfo(
        development_name="Test Development",
        town="Testton",
        postcode="IP14 1AA",
        strapline="A place to test",
        lifestyle_pillars=["Connected"],
        development_features=["Green space"],
    )


def _run(provider=None):
    deps = PipelineDeps(
        isochrone_provider=provider or StaticProvider(),
        isochrone_cache=InMemoryIsochroneCache(),
        reference=FakeReference(),
        geocode=lambda raw: Coordinate(lat=52.0, lng=1.0),
    )
    return run_catchment("IP14 1AA", _development(), ScoringConfig(), deps)


def test_runs_end_to_end_and_ranks_aligned_area_first():
    result = _run()
    assert [a.area_code for a in result.areas] == ["ALIGNED", "RICH"]
    assert result.areas[0].rank == 1
    assert result.areas[1].rank == 2
    # Income fit should reward alignment over raw wealth.
    assert result.areas[0].score.total > result.areas[1].score.total


def test_every_area_has_a_valid_battlecard():
    result = _run()
    assert set(result.battlecards) == {"ALIGNED", "RICH"}
    for code, card in result.battlecards.items():
        Battlecard.model_validate(card.model_dump(by_alias=True))
        assert card.area_code == code
    assert result.battlecards["ALIGNED"].rank == 1


def test_proportion_inside_carried_through():
    result = _run()
    aligned = next(a for a in result.areas if a.area_code == "ALIGNED")
    rich = next(a for a in result.areas if a.area_code == "RICH")
    assert aligned.proportion_inside == 1.0
    assert rich.proportion_inside == 0.5


def test_isochrone_cached_across_repeat_runs():
    provider = StaticProvider()
    deps = PipelineDeps(
        isochrone_provider=provider,
        isochrone_cache=InMemoryIsochroneCache(),
        reference=FakeReference(),
        geocode=lambda raw: Coordinate(lat=52.0, lng=1.0),
    )
    run_catchment("IP14 1AA", _development(), ScoringConfig(), deps)
    run_catchment("IP14 1AA", _development(), ScoringConfig(), deps)
    assert provider.calls == 1  # second run served from cache


def test_income_context_uses_catchment_extremes():
    card = _run().battlecards["ALIGNED"]
    income_chart = card.visual_summary.charts.household_income
    # Lowest and highest mean income across the two areas drive the callouts.
    assert income_chart.lowest_la.name == "Aligned Area"
    assert income_chart.highest_la.name == "Rich Area"
