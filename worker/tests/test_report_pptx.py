"""The multi-slide report deck renders, and the combined card aggregates
robustly when ONS household counts are missing.

These guard the regressions behind the PPTX review: a blank tenure donut and a
false 0% owner-occupied when household counts (TS003) are not loaded, caused by
household-weighted rates collapsing to a coerced zero.
"""

from __future__ import annotations

from landlynk_worker.battlecard import (
    DevelopmentInfo,
    IncomeContext,
    assemble_battlecard,
    render_report_pptx,
)
from landlynk_worker.battlecard.combine import (
    aggregate_profiles,
    build_combined_battlecard,
)
from landlynk_worker.scoring import (
    AgeProfile,
    AreaProfile,
    ScoringConfig,
    TenureMix,
    compute_score,
)


def _profile(households: int | None, tenure: TenureMix, pop: int = 8000) -> AreaProfile:
    return AreaProfile(
        area_code="E02000001",
        area_type="MSOA",
        population=pop,
        households=households,
        median_income=60000,
        mean_income=68000,
        median_age=39,
        tenure=tenure,
        age=AgeProfile(0.18, 0.30, 0.28, 0.18, 0.06),
        family_household_share=0.55,
        proportion_inside=1.0,
    )


def _card_from(profile: AreaProfile):
    config = ScoringConfig()
    return assemble_battlecard(
        profile,
        config,
        compute_score(profile, config),
        rank=1,
        development=DevelopmentInfo(
            "Westhill", "Kettering", "NN15 7FJ", "Room to grow", ["Green"], ["Park"]
        ),
        income_context=IncomeContext("Corby", 52000, "Oundle", 71000),
    )


def test_report_deck_renders():
    pptx = render_report_pptx(_card_from(_profile(3200, TenureMix(0.3, 0.4, 0.1, 0.2))))
    assert pptx[:2] == b"PK"  # an Office Open XML zip
    assert len(pptx) > 5000


def test_report_deck_renders_without_a_brand_logo():
    # No logo: the deck must still render (falls back to the LandLynk wordmark).
    pptx = render_report_pptx(
        _card_from(_profile(3200, TenureMix(0.3, 0.4, 0.1, 0.2))), logo=None
    )
    assert pptx[:2] == b"PK"


def test_tenure_aggregates_on_population_when_households_missing():
    # Household counts absent (TS003 not loaded) but tenure present (TS054). The
    # combined tenure must come through population-weighted, not collapse to zero.
    tenure = TenureMix(0.30, 0.40, 0.05, 0.25)
    agg = aggregate_profiles(
        [_profile(None, tenure, pop=6000), _profile(None, tenure, pop=4000)]
    )
    assert agg.tenure.owns_outright == 0.30
    assert agg.tenure.private_rented == 0.25
    assert agg.households is None  # counts are genuinely unknown, not zero


def test_suppressed_tenure_stays_none_not_zero():
    # When tenure is suppressed everywhere, the aggregate stays None: a missing
    # cell must never read as a real zero (house-standards.md).
    none_tenure = TenureMix(None, None, None, None)
    agg = aggregate_profiles([_profile(3200, none_tenure), _profile(2800, none_tenure)])
    assert agg.tenure.owns_outright is None
    assert agg.tenure.social_rented is None


def test_combined_card_owner_occupied_present_without_household_counts():
    # End to end through the stored-payload path: per-area cards with tenure but
    # no household count must still yield a real owner-occupied figure and a
    # populated tenure chart in the combined card.
    payload = _card_from(_profile(3200, TenureMix(0.30, 0.40, 0.05, 0.25))).model_dump(
        by_alias=True
    )
    payload["visualSummary"]["keyStatistics"]["householdsCatchment"] = {
        "value": None,
        "suppressed": True,
    }
    combined = build_combined_battlecard([payload, payload], names={}, config_dict=None)
    owner = combined.visual_summary.key_statistics.owner_occupied_percentage.value
    assert owner is not None and owner > 0
    tenure = combined.visual_summary.charts.housing_tenure
    assert tenure.owns_outright.value == 30.0
