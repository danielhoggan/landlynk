"""The pipeline orchestrator: input to ranked, scored Battlecards.

Ties the stages together in order (SCOPING.md Section 7):
resolve, isochrone, intersect, join, score, assemble. Dependencies (geocoder,
isochrone provider and cache, reference data) are injected so the whole flow is
unit tested offline with fakes and points at live services in production.

This runs in the Python worker, never in a Next.js request cycle.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from shapely.geometry import mapping, shape

from ..battlecard import DevelopmentInfo, IncomeContext, assemble_battlecard
from ..battlecard.schema import Battlecard
from ..scoring.profile import ScoringConfig
from ..scoring.score import ScoreBreakdown, compute_score
from .intersect import intersect_catchment
from .isochrone import IsochroneCache, IsochroneParams, IsochroneProvider, get_isochrone
from .reference import ReferenceData
from .resolve import Coordinate, resolve_input


@dataclass(frozen=True)
class ScoredArea:
    area_code: str
    area_type: str
    name: str
    proportion_inside: float
    score: ScoreBreakdown
    rank: int
    # GeoJSON geometry for the map. Optional so test fixtures can omit it.
    geometry: dict | None = None


@dataclass(frozen=True)
class CatchmentResult:
    coordinate: Coordinate
    isochrone: dict
    areas: list[ScoredArea]
    battlecards: dict[str, Battlecard]


@dataclass
class PipelineDeps:
    isochrone_provider: IsochroneProvider
    isochrone_cache: IsochroneCache
    reference: ReferenceData
    # Geocoder is injectable so tests avoid the network; defaults to the real one.
    geocode: Callable[[str], Coordinate] = resolve_input


def _income_context(areas: list, references: dict) -> IncomeContext:
    """Lowest and highest mean income across the catchment, for the chart callouts.

    Areas with suppressed income are skipped so a gap does not masquerade as a
    low value.
    """
    priced = [
        (a.area_code, references[a.area_code])
        for a in areas
        if references[a.area_code].profile.mean_income is not None
    ]
    if not priced:
        return IncomeContext(
            lowest_la_name="Not available",
            lowest_la_value=None,
            highest_la_name="Not available",
            highest_la_value=None,
        )
    lowest = min(priced, key=lambda p: p[1].profile.mean_income)
    highest = max(priced, key=lambda p: p[1].profile.mean_income)
    return IncomeContext(
        lowest_la_name=lowest[1].name,
        lowest_la_value=lowest[1].profile.mean_income,
        highest_la_name=highest[1].name,
        highest_la_value=highest[1].profile.mean_income,
    )


def run_catchment(
    raw_input: str,
    development: DevelopmentInfo,
    config: ScoringConfig,
    deps: PipelineDeps,
    area_type: str = "MSOA",
) -> CatchmentResult:
    """Run the full pipeline and return ranked areas with their Battlecards."""
    # 1. Resolve input to a coordinate.
    coordinate = deps.geocode(raw_input)

    # 2. Isochrone, cached by coordinate and parameters.
    params = IsochroneParams(
        lat=coordinate.lat,
        lng=coordinate.lng,
        drive_time_minutes=config.drive_time_minutes,
    )
    isochrone = get_isochrone(params, deps.isochrone_provider, deps.isochrone_cache)
    isochrone_shape = shape(isochrone)

    # 3. Intersect candidate boundaries against the isochrone.
    candidates = deps.reference.candidate_area_geometries(isochrone, area_type)
    matches = intersect_catchment(candidates, isochrone_shape, config.overlap_threshold)
    geometry_by_code = {c.area_code: mapping(c.geometry) for c in candidates}

    # 4 and 5. Join reference data and score each retained area.
    references = {
        m.area_code: deps.reference.area_reference(
            m.area_code, m.area_type, m.proportion_inside
        )
        for m in matches
    }
    scored = [
        (m, compute_score(references[m.area_code].profile, config)) for m in matches
    ]
    # Rank by total score, descending. Ties keep intersect order (most covered first).
    scored.sort(key=lambda pair: pair[1].total, reverse=True)

    areas: list[ScoredArea] = []
    ordered_for_context = [m for m, _ in scored]
    income_context = _income_context(ordered_for_context, references)

    # 6. Assemble one Battlecard per area from the single payload contract.
    battlecards: dict[str, Battlecard] = {}
    for rank, (match, score) in enumerate(scored, start=1):
        ref = references[match.area_code]
        areas.append(
            ScoredArea(
                area_code=match.area_code,
                area_type=match.area_type,
                name=ref.name,
                proportion_inside=match.proportion_inside,
                score=score,
                rank=rank,
                geometry=geometry_by_code.get(match.area_code),
            )
        )
        battlecards[match.area_code] = assemble_battlecard(
            profile=ref.profile,
            config=config,
            score=score,
            rank=rank,
            development=development,
            income_context=income_context,
        )

    return CatchmentResult(
        coordinate=coordinate,
        isochrone=isochrone,
        areas=areas,
        battlecards=battlecards,
    )
