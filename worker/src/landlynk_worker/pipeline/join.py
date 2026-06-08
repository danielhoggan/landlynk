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

from ..scoring.profile import AgeProfile, AreaProfile, TenureMix


def build_area_profile(
    area_code: str,
    area_type: str,
    proportion_inside: float,
    demographics_row: dict,
    tenure_row: dict,
    income_row: dict,
) -> AreaProfile:
    """Map reference rows to an AreaProfile, preserving suppression as None.

    Each row is a dict keyed by the reference table column names. Missing or
    suppressed values arrive as None and stay None.
    """
    return AreaProfile(
        area_code=area_code,
        area_type=area_type,
        population=demographics_row.get("population"),
        households=demographics_row.get("households"),
        median_income=income_row.get("median_income"),
        mean_income=income_row.get("mean_income"),
        tenure=TenureMix(
            owns_outright=tenure_row.get("owns_outright"),
            owns_with_mortgage=tenure_row.get("owns_with_mortgage"),
            social_rented=tenure_row.get("social_rented"),
            private_rented=tenure_row.get("private_rented"),
        ),
        age=AgeProfile(
            age_0_15=demographics_row.get("age_0_15"),
            age_16_34=demographics_row.get("age_16_34"),
            age_35_54=demographics_row.get("age_35_54"),
            age_55_74=demographics_row.get("age_55_74"),
            age_75_plus=demographics_row.get("age_75_plus"),
        ),
        family_household_share=demographics_row.get("family_household_share"),
        proportion_inside=proportion_inside,
    )
