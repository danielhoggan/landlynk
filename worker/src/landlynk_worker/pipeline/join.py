"""Stage 4: join ONS reference data onto the retained areas.

For each area kept by the intersect, pull demographics, tenure and income from
the versioned reference tables and assemble an :class:`AreaProfile` for scoring.

ONS suppression and rounding are handled explicitly: a suppressed cell becomes
None on the profile, never zero (house-standards.md, data handling). Data
confidence is carried through for the deep-dive rather than hiding gaps.

The reference reads are wired to Postgres in implementation. This module owns
the mapping from raw reference rows to the scoring profile.
"""

from __future__ import annotations

from decimal import Decimal

from ..scoring.profile import AgeProfile, AreaProfile, TenureMix


def _f(value: object) -> float | None:
    """Coerce a DB numeric to float, preserving None.

    Postgres NUMERIC columns arrive as decimal.Decimal via psycopg, which cannot
    be mixed with float in the scoring arithmetic. Normalise to float here.
    """
    if value is None:
        return None
    if isinstance(value, (Decimal, int, float)):
        return float(value)
    return float(str(value))


def _i(value: object) -> int | None:
    """Coerce a DB numeric to int, preserving None."""
    if value is None:
        return None
    return int(value)


def build_area_profile(
    area_code: str,
    area_type: str,
    proportion_inside: float,
    demographics_row: dict,
    tenure_row: dict,
    income_row: dict,
    house_price_row: dict | None = None,
    context: dict[str, float] | None = None,
) -> AreaProfile:
    """Map reference rows to an AreaProfile, preserving suppression as None.

    Each row is a dict keyed by the reference table column names. Missing or
    suppressed values arrive as None and stay None. DB numerics (Decimal) are
    coerced to float/int so scoring arithmetic does not mix Decimal with float.

    Age bands are stored as counts but the profile carries them as shares of the
    area population, which is what the scoring and charts expect.
    """
    population = _i(demographics_row.get("population"))

    def age_share(key: str) -> float | None:
        count = _f(demographics_row.get(key))
        if count is None or not population:
            return None
        return count / population

    return AreaProfile(
        area_code=area_code,
        area_type=area_type,
        population=population,
        households=_i(demographics_row.get("households")),
        median_income=_f(income_row.get("median_income")),
        mean_income=_f(income_row.get("mean_income")),
        median_age=_f(demographics_row.get("median_age")),
        tenure=TenureMix(
            owns_outright=_f(tenure_row.get("owns_outright")),
            owns_with_mortgage=_f(tenure_row.get("owns_with_mortgage")),
            social_rented=_f(tenure_row.get("social_rented")),
            private_rented=_f(tenure_row.get("private_rented")),
        ),
        age=AgeProfile(
            age_0_15=age_share("age_0_15"),
            age_16_34=age_share("age_16_34"),
            age_35_54=age_share("age_35_54"),
            age_55_74=age_share("age_55_74"),
            age_75_plus=age_share("age_75_plus"),
        ),
        family_household_share=_f(demographics_row.get("family_household_share")),
        proportion_inside=proportion_inside,
        median_house_price=_f((house_price_row or {}).get("median_price")),
        context=context or {},
    )
