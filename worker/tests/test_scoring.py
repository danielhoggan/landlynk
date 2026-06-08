"""Scoring is deterministic and explainable.

Given a known area profile and config, the score and rank are deterministic and
asserted (house-standards.md, testing).
"""

from __future__ import annotations

from landlynk_worker.scoring import (
    AgeProfile,
    AreaProfile,
    PriceBand,
    ScoringConfig,
    TenureMix,
    compute_score,
    score_addressable_scale,
    score_income_fit,
)


def make_profile(**overrides) -> AreaProfile:
    base = dict(
        area_code="E02000001",
        area_type="MSOA",
        population=8000,
        households=3200,
        median_income=60_000,
        mean_income=68_000,
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
        proportion_inside=1.0,
    )
    base.update(overrides)
    return AreaProfile(**base)


def test_income_fit_rewards_alignment_not_wealth():
    config = ScoringConfig(price_band=PriceBand(250_000, 400_000))
    target = config.price_band.midpoint / config.affordability_multiple  # ~72,222

    aligned = make_profile(median_income=target)
    too_high = make_profile(median_income=target * 2)

    aligned_score = score_income_fit(aligned, config).raw_score
    high_score = score_income_fit(too_high, config).raw_score

    assert aligned_score == 1.0
    assert high_score < aligned_score


def test_income_fit_handles_suppressed_income():
    config = ScoringConfig()
    suppressed = make_profile(median_income=None)
    signal = score_income_fit(suppressed, config)
    assert signal.raw_score == 0.0
    assert "suppressed" in signal.rationale.lower()


def test_addressable_scale_weighted_by_proportion_inside():
    config = ScoringConfig()
    fully_in = make_profile(population=50_000, proportion_inside=1.0)
    half_in = make_profile(population=50_000, proportion_inside=0.5)

    full = score_addressable_scale(fully_in, config).raw_score
    half = score_addressable_scale(half_in, config).raw_score

    assert full > half


def test_compute_score_is_deterministic():
    config = ScoringConfig()
    profile = make_profile()

    first = compute_score(profile, config)
    second = compute_score(profile, config)

    assert first.total == second.total
    assert first.band == second.band
    assert [c.contribution for c in first.contributions] == [
        c.contribution for c in second.contributions
    ]


def test_compute_score_in_unit_range_and_banded():
    config = ScoringConfig()
    result = compute_score(make_profile(), config)
    assert 0.0 <= result.total <= 1.0
    assert result.band in {"high", "mid", "low"}
    # Total equals the sum of contributions (transparent blend).
    assert abs(result.total - sum(c.contribution for c in result.contributions)) < 1e-9


def test_weights_need_not_sum_to_one():
    # Doubling all weights normalises out to the same score.
    base = ScoringConfig()
    doubled = ScoringConfig(weights={k: v * 2 for k, v in base.weights.items()})
    profile = make_profile()
    assert (
        abs(compute_score(profile, base).total - compute_score(profile, doubled).total)
        < 1e-9
    )


def test_zero_weights_raise():
    config = ScoringConfig(weights={k: 0.0 for k in ScoringConfig().weights})
    try:
        compute_score(make_profile(), config)
    except ValueError as exc:
        assert "positive" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError for zero weights")
