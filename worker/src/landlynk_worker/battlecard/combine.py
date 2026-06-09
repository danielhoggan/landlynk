"""Combine several areas into one aggregate Battlecard.

A wider-catchment card: select MSOAs (or take the whole catchment) and merge
them into a single profile, then assemble one Battlecard from it. Population and
household counts sum; income, age and tenure are weighted means across the
selected areas. Aggregated medians are approximations of true medians, so the
combined card is labelled indicative.

Reconstructed from the stored Battlecard payloads (no raw profiles are kept), so
it works on any saved run.
"""

from __future__ import annotations

from collections.abc import Callable

from ..scoring.profile import (
    AgeProfile,
    AreaProfile,
    PriceBand,
    ScoringConfig,
    TenureMix,
)
from ..scoring.score import compute_score, relative_band
from .assemble import DevelopmentInfo, IncomeContext, assemble_battlecard
from .schema import Battlecard

_AGE_BANDS = ("age_0_15", "age_16_34", "age_35_54", "age_55_74", "age_75_plus")


def _val(node: dict | None) -> float | None:
    if not node:
        return None
    return node.get("value")


def _share(node: dict | None) -> float | None:
    v = _val(node)
    return None if v is None else v / 100.0


def reconstruct_profile(payload: dict) -> AreaProfile:
    """Rebuild an AreaProfile from a stored Battlecard payload.

    population/households are the area's counts inside the catchment, so the
    reconstructed profile uses proportion_inside = 1.0 (already-inside values).
    """
    vs = payload.get("visualSummary") or {}
    ks = vs.get("keyStatistics") or {}
    charts = vs.get("charts") or {}
    tenure = charts.get("housingTenure") or {}
    income = charts.get("householdIncome") or {}
    ages = charts.get("ageDemographics") or []

    age_shares = [_share(a.get("percentage")) or 0.0 for a in ages][:5]
    age_shares += [0.0] * (5 - len(age_shares))

    family = _val(ks.get("familyHouseholdShare"))
    return AreaProfile(
        area_code=payload.get("areaCode", "combined"),
        area_type=payload.get("areaType", "MSOA"),
        population=_val(ks.get("populationCatchment")),
        households=_val(ks.get("householdsCatchment")),
        median_income=_val(income.get("median")),
        mean_income=_val(ks.get("averageHouseholdIncome")) or _val(income.get("mean")),
        median_age=_val(ks.get("medianAge")),
        tenure=TenureMix(
            owns_outright=_share(tenure.get("ownsOutright")) or 0.0,
            owns_with_mortgage=_share(tenure.get("ownsWithMortgage")) or 0.0,
            social_rented=_share(tenure.get("socialRented")) or 0.0,
            private_rented=_share(tenure.get("privateRented")) or 0.0,
        ),
        age=AgeProfile(*age_shares),
        family_household_share=None if family is None else family / 100.0,
        proportion_inside=1.0,
        median_house_price=_val(ks.get("medianHousePrice")),
    )


def _wavg(pairs: list[tuple[float | None, float]]) -> float | None:
    """Weighted average over (value, weight), skipping None values."""
    num = 0.0
    den = 0.0
    for value, weight in pairs:
        if value is not None and weight > 0:
            num += value * weight
            den += weight
    return num / den if den else None


def aggregate_profiles(profiles: list[AreaProfile]) -> AreaProfile:
    """Merge area profiles into one: sums of counts, weighted-mean rates."""
    total_pop = sum(p.population or 0.0 for p in profiles)
    total_hh = sum(p.households or 0.0 for p in profiles)

    def by_pop(get: Callable[[AreaProfile], float | None]) -> float | None:
        return _wavg([(get(p), p.population or 0.0) for p in profiles])

    def by_hh(get: Callable[[AreaProfile], float | None]) -> float | None:
        return _wavg([(get(p), p.households or 0.0) for p in profiles])

    age_bands = {
        band: by_pop(lambda p, b=band: getattr(p.age, b)) or 0.0 for band in _AGE_BANDS
    }
    return AreaProfile(
        area_code="combined",
        area_type=profiles[0].area_type if profiles else "MSOA",
        population=total_pop or None,
        households=total_hh or None,
        median_income=by_pop(lambda p: p.median_income),
        mean_income=by_pop(lambda p: p.mean_income),
        median_age=by_pop(lambda p: p.median_age),
        tenure=TenureMix(
            owns_outright=by_hh(lambda p: p.tenure.owns_outright) or 0.0,
            owns_with_mortgage=by_hh(lambda p: p.tenure.owns_with_mortgage) or 0.0,
            social_rented=by_hh(lambda p: p.tenure.social_rented) or 0.0,
            private_rented=by_hh(lambda p: p.tenure.private_rented) or 0.0,
        ),
        age=AgeProfile(**age_bands),
        family_household_share=by_hh(lambda p: p.family_household_share),
        proportion_inside=1.0,
        median_house_price=by_hh(lambda p: p.median_house_price),
    )


def _config_from_dict(d: dict | None) -> ScoringConfig:
    base = ScoringConfig()
    if not d:
        return base
    pb = d.get("priceBand") or {}
    return ScoringConfig(
        weights=d.get("weights") or base.weights,
        price_band=PriceBand(
            frm=pb.get("from", base.price_band.frm),
            to=pb.get("to", base.price_band.to),
        ),
        bed_range=d.get("bedRange", base.bed_range),
        overlap_threshold=d.get("overlapThreshold", base.overlap_threshold),
        drive_time_minutes=d.get("driveTimeMinutes", base.drive_time_minutes),
        affordability_multiple=d.get(
            "affordabilityMultiple", base.affordability_multiple
        ),
        tenure_preference=d.get("tenurePreference") or base.tenure_preference,
        age_preference=d.get("agePreference") or base.age_preference,
        scale_saturation=d.get("scaleSaturation", base.scale_saturation),
    )


def build_combined_battlecard(
    payloads: list[dict],
    names: dict[str, str],
    config_dict: dict | None,
    label: str = "Combined catchment",
) -> Battlecard:
    """Assemble one Battlecard for the combined set of areas."""
    profiles = [reconstruct_profile(p) for p in payloads]
    aggregate = aggregate_profiles(profiles)
    config = _config_from_dict(config_dict)
    score = compute_score(aggregate, config)

    header = (payloads[0].get("visualSummary") or {}).get("header") or {}
    vs0 = payloads[0].get("visualSummary") or {}
    development = DevelopmentInfo(
        development_name=header.get("developmentName", "Catchment"),
        town=f"{label}: {len(payloads)} areas",
        postcode=None,
        strapline=header.get("strapline", ""),
        lifestyle_pillars=header.get("lifestylePillars") or [],
        development_features=vs0.get("developmentFeatures") or [],
    )

    # Income callouts: lowest and highest mean income across the selected areas.
    priced = [
        (names.get(p.get("areaCode", ""), p.get("areaCode", "")), prof.mean_income)
        for p, prof in zip(payloads, profiles, strict=False)
        if prof.mean_income is not None
    ]
    if priced:
        lo = min(priced, key=lambda x: x[1])
        hi = max(priced, key=lambda x: x[1])
        income_context = IncomeContext(lo[0], lo[1], hi[0], hi[1])
    else:
        income_context = IncomeContext("Not available", None, "Not available", None)

    card = assemble_battlecard(
        profile=aggregate,
        config=config,
        score=score,
        rank=1,
        development=development,
        income_context=income_context,
    )
    card.score.band = relative_band(1, 1)
    return card
