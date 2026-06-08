"""build_area_profile coerces DB numerics and turns age counts into shares."""

from __future__ import annotations

from decimal import Decimal

from landlynk_worker.pipeline.join import build_area_profile


def test_decimal_values_coerced_and_age_to_shares():
    demographics = {
        "population": 1000,
        "households": 400,
        "age_0_15": Decimal("150"),  # counts, stored NUMERIC -> Decimal
        "age_16_34": Decimal("300"),
        "age_35_54": Decimal("250"),
        "age_55_74": Decimal("200"),
        "age_75_plus": Decimal("100"),
        "median_age": Decimal("39"),
        "family_household_share": Decimal("0.55"),
    }
    tenure = {
        "owns_outright": Decimal("0.25"),
        "owns_with_mortgage": Decimal("0.40"),
        "social_rented": Decimal("0.10"),
        "private_rented": Decimal("0.25"),
    }
    income = {"median_income": Decimal("48000"), "mean_income": Decimal("52000.5")}

    profile = build_area_profile("E02000001", "MSOA", 0.8, demographics, tenure, income)

    # Coerced to float, no Decimal arithmetic errors downstream.
    assert isinstance(profile.mean_income, float)
    assert profile.mean_income == 52000.5
    assert isinstance(profile.tenure.owns_outright, float)
    # Age counts became shares of population.
    assert profile.age.age_0_15 == 0.15
    assert profile.age.age_16_34 == 0.30
    assert isinstance(profile.median_age, float)


def test_age_share_none_without_population():
    demographics = {"population": None, "age_0_15": Decimal("150")}
    profile = build_area_profile("E1", "MSOA", 1.0, demographics, {}, {})
    assert profile.age.age_0_15 is None


def test_scoring_runs_on_decimal_sourced_profile():
    # End to end: a Decimal-sourced profile must score without type errors.
    from landlynk_worker.scoring import ScoringConfig, compute_score

    demographics = {
        "population": 1000,
        "households": 400,
        "age_0_15": Decimal("150"),
        "age_16_34": Decimal("300"),
        "age_35_54": Decimal("250"),
        "age_55_74": Decimal("200"),
        "age_75_plus": Decimal("100"),
        "median_age": Decimal("39"),
        "family_household_share": Decimal("0.55"),
    }
    tenure = {
        "owns_outright": Decimal("0.25"),
        "owns_with_mortgage": Decimal("0.40"),
        "social_rented": Decimal("0.10"),
        "private_rented": Decimal("0.25"),
    }
    income = {"median_income": Decimal("60000"), "mean_income": Decimal("68000")}
    profile = build_area_profile("E1", "MSOA", 0.8, demographics, tenure, income)
    result = compute_score(profile, ScoringConfig())
    assert 0.0 <= result.total <= 1.0
