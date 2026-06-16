"""Battlecard assembly produces a valid payload with signal-driven commentary.

Covers the suppression contract (null, never zero) and the house prose
conventions (no em dashes, no Oxford commas, no markdown headers).
"""

from __future__ import annotations

from landlynk_worker.battlecard import (
    DevelopmentInfo,
    IncomeContext,
    assemble_battlecard,
)
from landlynk_worker.battlecard.schema import Battlecard
from landlynk_worker.scoring import (
    AgeProfile,
    AreaProfile,
    ScoringConfig,
    TenureMix,
    compute_score,
)


def make_profile(**overrides) -> AreaProfile:
    base = dict(
        area_code="E02000001",
        area_type="MSOA",
        population=8000,
        households=3200,
        median_income=60_000,
        mean_income=68_000,
        median_age=39,
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
        proportion_inside=0.8,
    )
    base.update(overrides)
    return AreaProfile(**base)


def _development() -> DevelopmentInfo:
    return DevelopmentInfo(
        development_name="Abbots Vale",
        town="Stowmarket",
        postcode="IP14 1AA",
        strapline="Room to grow",
        lifestyle_pillars=["Connected", "Green", "Family"],
        development_features=["Open green space", "Primary school nearby"],
    )


def _income_context() -> IncomeContext:
    return IncomeContext(
        lowest_la_name="Ipswich",
        lowest_la_value=52_000,
        highest_la_name="Babergh",
        highest_la_value=71_000,
    )


def _assemble(profile: AreaProfile) -> Battlecard:
    config = ScoringConfig()
    score = compute_score(profile, config)
    return assemble_battlecard(
        profile,
        config,
        score,
        rank=1,
        development=_development(),
        income_context=_income_context(),
    )


def test_no_price_set_suppresses_pricing():
    # A run with no target price ranks on a neutral default but must not present
    # a price story: price from is null and the rationale says so.
    from dataclasses import replace

    profile = make_profile()
    config = replace(ScoringConfig(), price_set=False)
    card = assemble_battlecard(
        profile,
        config,
        compute_score(profile, config),
        rank=1,
        development=_development(),
        income_context=_income_context(),
    )
    assert card.visual_summary.key_statistics.price_from.value is None
    assert card.pricing_rationale.price_from.value is None
    assert "no pricing read" in card.pricing_rationale.positioning.lower()


def test_assembles_a_valid_battlecard():
    card = _assemble(make_profile())
    # Re-validate through the schema to prove the payload is contract-clean.
    Battlecard.model_validate(card.model_dump(by_alias=True))
    assert card.area_code == "E02000001"
    assert card.rank == 1
    assert len(card.visual_summary.charts.age_demographics) == 5


def test_population_catchment_weighted_by_proportion_inside():
    card = _assemble(make_profile(population=10_000, proportion_inside=0.8))
    assert card.visual_summary.key_statistics.population_catchment.value == 8000


def test_owner_occupied_combines_ownership_tenures():
    card = _assemble(make_profile())
    # 25% outright + 40% mortgage = 65%.
    assert card.visual_summary.key_statistics.owner_occupied_percentage.value == 65.0


def test_suppressed_income_is_null_not_zero():
    card = _assemble(make_profile(mean_income=None))
    avg = card.visual_summary.key_statistics.average_household_income
    assert avg.value is None
    assert avg.suppressed is True


def test_audience_tiers_ordered_by_signal_strength():
    # Heavy private rented should put first-time buyers first.
    profile = make_profile(
        tenure=TenureMix(
            owns_outright=0.10,
            owns_with_mortgage=0.20,
            social_rented=0.10,
            private_rented=0.60,
        )
    )
    card = _assemble(profile)
    primary = next(
        m for m in card.visual_summary.audience_messaging if m.tier == "primary"
    )
    assert primary.audience == "First-time buyers"


def test_income_commentary_flags_wide_spread():
    card = _assemble(make_profile(median_income=40_000, mean_income=60_000))
    assert "above the median" in card.income_and_tenure.income_commentary


def test_prose_obeys_house_conventions():
    card = _assemble(make_profile())
    prose = " ".join(
        [
            card.income_and_tenure.income_commentary,
            card.income_and_tenure.tenure_commentary,
            *[c.body for c in card.audience_and_demographics.audience_tiers],
            *[c.body for c in card.audience_and_demographics.age_cohorts],
        ]
    )
    assert "—" not in prose  # no em dashes
    assert "#" not in prose  # no markdown headers
    # No Oxford comma: avoid the ", and" pattern in generated prose.
    assert ", and " not in prose


def test_score_contributions_use_contract_signal_names():
    card = _assemble(make_profile())
    signals = {c.signal for c in card.score.contributions}
    assert signals == {
        "incomeFit",
        "tenureSignal",
        "ageSkew",
        "addressableScale",
        "householdType",
    }


# --- Data-driven sections beyond the reference card --------------------------


def test_pricing_rationale_implied_price_from_income():
    card = _assemble(make_profile(median_income=60_000))
    # 60,000 * 4.5 default multiple = 270,000.
    assert card.pricing_rationale.implied_affordable_price.value == 270_000
    assert card.pricing_rationale.affordability_multiple == 4.5
    assert card.pricing_rationale.positioning


def test_pricing_rationale_flags_unaffordable_entry():
    # Low income, high price band entry: positioning should target equity movers.
    profile = make_profile(median_income=20_000)
    from landlynk_worker.scoring import PriceBand

    config = ScoringConfig(price_band=PriceBand(400_000, 600_000))
    score = compute_score(profile, config)
    card = assemble_battlecard(
        profile,
        config,
        score,
        rank=1,
        development=_development(),
        income_context=_income_context(),
    )
    assert "above local means" in card.pricing_rationale.positioning


def test_addressable_segments_counts_inside_catchment():
    # 3200 households * 0.8 inside = 2560; private rented 0.25 -> 640.
    card = _assemble(make_profile(households=3200, proportion_inside=0.8))
    assert card.addressable_segments.first_time_buyer_pipeline.value == 640
    assert card.addressable_segments.downsizer_pool.value == 640  # outright 0.25
    assert card.addressable_segments.family_households.value == round(2560 * 0.55)


def test_data_confidence_high_when_complete():
    card = _assemble(make_profile())
    assert card.data_confidence.level == "high"
    assert card.data_confidence.suppressed_fields == []


def test_data_confidence_drops_with_suppression():
    profile = make_profile(
        median_income=None, mean_income=None, population=None, households=None
    )
    config = ScoringConfig()
    score = compute_score(profile, config)
    card = assemble_battlecard(
        profile,
        config,
        score,
        rank=1,
        development=_development(),
        income_context=_income_context(),
    )
    assert card.data_confidence.level == "low"
    assert "income" in card.data_confidence.suppressed_fields


def test_catchment_context_income_index():
    from landlynk_worker.battlecard import CatchmentStats

    profile = make_profile(mean_income=80_000, population=10_000, proportion_inside=1.0)
    config = ScoringConfig()
    score = compute_score(profile, config)
    card = assemble_battlecard(
        profile,
        config,
        score,
        rank=1,
        development=_development(),
        income_context=_income_context(),
        catchment_stats=CatchmentStats(
            mean_income=64_000, total_population_inside=50_000
        ),
    )
    # 80,000 / 64,000 * 100 = 125; 10,000 / 50,000 = 20%.
    assert card.catchment_context.income_index.value == 125
    assert card.catchment_context.share_of_catchment_population.value == 20.0
