"""Predefined audience segments for segment-first targeting.

A segment is a named bundle of scoring preferences: which age cohorts and tenure
mixes a product or service is aimed at, plus (for residential) a sensible bed
range. Choosing a segment on the form, or via a saved profile, lets a user ask
"rank this catchment for first time buyers" rather than hand-tuning preference
vectors. Segments feed the existing transparent scoring; they change the age and
tenure preference vectors that score_age_skew and score_tenure_signal consume.

Segments are scoped to an industry, because audiences differ by sector: a
housebuilder targets buyer types, a leisure operator targets member types. The
brand's industry decides which segments a user sees. Every segment, in every
industry, is still expressed in the same ONS terms (age cohorts and tenure),
because that is all the scoring can see. The vectors below are first-draft
demographic leanings and are meant to be tuned with the client.

Age cohorts: age_0_15, age_16_34, age_35_54, age_55_74, age_75_plus.
Tenure: owns_outright, owns_with_mortgage, social_rented, private_rented.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .profile import ScoringConfig

# Default bed range for non-residential segments. Bed mix is a housebuilder
# product concept; for other sectors it is inert metadata, kept neutral.
_NA_BEDS = "2 to 5"


@dataclass(frozen=True)
class Segment:
    id: str
    industry: str
    label: str
    description: str
    age_preference: dict[str, float]
    tenure_preference: dict[str, float]
    bed_range: str


SEGMENTS: dict[str, Segment] = {
    # --- residential development / house building --------------------------
    "first_time_buyer": Segment(
        id="first_time_buyer",
        industry="residential",
        label="First time buyers",
        description="Young renters stepping onto the ladder. Compact homes.",
        age_preference={"age_16_34": 1.0, "age_35_54": 0.3},
        tenure_preference={"private_rented": 1.0, "owns_with_mortgage": 0.4},
        bed_range="2 to 3",
    ),
    "second_stepper": Segment(
        id="second_stepper",
        industry="residential",
        label="Second steppers",
        description="Mortgaged owners trading up. Three bed family starts.",
        age_preference={"age_35_54": 1.0, "age_16_34": 0.4, "age_0_15": 0.4},
        tenure_preference={"owns_with_mortgage": 1.0, "private_rented": 0.3},
        bed_range="3 to 4",
    ),
    "growing_family": Segment(
        id="growing_family",
        industry="residential",
        label="Growing families",
        description="Mid-life households with children. Larger family homes.",
        age_preference={"age_35_54": 1.0, "age_0_15": 0.8},
        tenure_preference={"owns_with_mortgage": 1.0, "owns_outright": 0.3},
        bed_range="3 to 5",
    ),
    "downsizer": Segment(
        id="downsizer",
        industry="residential",
        label="Downsizers",
        description="Older outright owners releasing equity. Low maintenance.",
        age_preference={"age_55_74": 1.0, "age_75_plus": 0.7},
        tenure_preference={"owns_outright": 1.0, "owns_with_mortgage": 0.2},
        bed_range="2 to 3",
    ),
    "high_net_worth": Segment(
        id="high_net_worth",
        industry="residential",
        label="High net worth",
        description="Affluent established owners. Premium, larger homes.",
        age_preference={"age_35_54": 1.0, "age_55_74": 0.8},
        tenure_preference={"owns_outright": 1.0, "owns_with_mortgage": 0.6},
        bed_range="4 to 5",
    ),
    # --- retail and hospitality --------------------------------------------
    "urban_professionals": Segment(
        id="urban_professionals",
        industry="retail",
        label="Urban professionals",
        description="Younger working renters and owners with disposable income.",
        age_preference={"age_16_34": 1.0, "age_35_54": 0.5},
        tenure_preference={"private_rented": 1.0, "owns_with_mortgage": 0.5},
        bed_range=_NA_BEDS,
    ),
    "family_shoppers": Segment(
        id="family_shoppers",
        industry="retail",
        label="Family shoppers",
        description="Households with children doing the bulk of family spend.",
        age_preference={"age_35_54": 1.0, "age_0_15": 0.8},
        tenure_preference={"owns_with_mortgage": 1.0, "owns_outright": 0.3},
        bed_range=_NA_BEDS,
    ),
    "affluent_older_shoppers": Segment(
        id="affluent_older_shoppers",
        industry="retail",
        label="Affluent older shoppers",
        description="Established older owners with time and money to spend.",
        age_preference={"age_55_74": 1.0, "age_75_plus": 0.4},
        tenure_preference={"owns_outright": 1.0, "owns_with_mortgage": 0.4},
        bed_range=_NA_BEDS,
    ),
    "students_and_young_singles": Segment(
        id="students_and_young_singles",
        industry="retail",
        label="Students and young singles",
        description="Students and young single renters. Value and convenience.",
        age_preference={"age_16_34": 1.0},
        tenure_preference={"private_rented": 1.0, "social_rented": 0.3},
        bed_range=_NA_BEDS,
    ),
    # --- leisure and fitness -----------------------------------------------
    "young_actives": Segment(
        id="young_actives",
        industry="leisure",
        label="Young actives",
        description="Younger members for gym and high-intensity classes.",
        age_preference={"age_16_34": 1.0, "age_35_54": 0.4},
        tenure_preference={"private_rented": 0.8, "owns_with_mortgage": 0.5},
        bed_range=_NA_BEDS,
    ),
    "active_families": Segment(
        id="active_families",
        industry="leisure",
        label="Active families",
        description="Families using swimming, junior and family activities.",
        age_preference={"age_35_54": 1.0, "age_0_15": 0.8},
        tenure_preference={"owns_with_mortgage": 1.0, "owns_outright": 0.3},
        bed_range=_NA_BEDS,
    ),
    "active_retirees": Segment(
        id="active_retirees",
        industry="leisure",
        label="Active retirees",
        description="Older members for low-impact classes, swimming and racquets.",
        age_preference={"age_55_74": 1.0, "age_75_plus": 0.5},
        tenure_preference={"owns_outright": 1.0, "owns_with_mortgage": 0.4},
        bed_range=_NA_BEDS,
    ),
    # --- healthcare and care -----------------------------------------------
    "families_and_children": Segment(
        id="families_and_children",
        industry="healthcare",
        label="Families and children",
        description="Households with children, driving paediatric and GP demand.",
        age_preference={"age_0_15": 1.0, "age_35_54": 0.8},
        tenure_preference={
            "owns_with_mortgage": 0.7,
            "private_rented": 0.5,
            "social_rented": 0.5,
        },
        bed_range=_NA_BEDS,
    ),
    "working_age_adults": Segment(
        id="working_age_adults",
        industry="healthcare",
        label="Working age adults",
        description="Working age population for routine and occupational care.",
        age_preference={"age_35_54": 1.0, "age_16_34": 0.7},
        tenure_preference={
            "owns_with_mortgage": 0.7,
            "private_rented": 0.6,
            "owns_outright": 0.4,
        },
        bed_range=_NA_BEDS,
    ),
    "older_adults_care": Segment(
        id="older_adults_care",
        industry="healthcare",
        label="Older adults",
        description="Older population with higher and longer-term care needs.",
        age_preference={"age_75_plus": 1.0, "age_55_74": 0.8},
        tenure_preference={
            "owns_outright": 0.8,
            "social_rented": 0.4,
            "owns_with_mortgage": 0.3,
        },
        bed_range=_NA_BEDS,
    ),
    "higher_needs_communities": Segment(
        id="higher_needs_communities",
        industry="healthcare",
        label="Higher needs communities",
        description="Areas of higher need, proxied by social-rented tenure.",
        age_preference={"age_0_15": 0.5, "age_35_54": 0.6, "age_75_plus": 0.6},
        tenure_preference={"social_rented": 1.0, "private_rented": 0.5},
        bed_range=_NA_BEDS,
    ),
    # --- education ----------------------------------------------------------
    "early_years_primary": Segment(
        id="early_years_primary",
        industry="education",
        label="Early years and primary",
        description="Young families driving nursery and primary demand.",
        age_preference={"age_0_15": 1.0, "age_35_54": 0.7},
        tenure_preference={
            "owns_with_mortgage": 0.7,
            "social_rented": 0.5,
            "private_rented": 0.5,
        },
        bed_range=_NA_BEDS,
    ),
    "secondary_families": Segment(
        id="secondary_families",
        industry="education",
        label="Secondary families",
        description="Households with teenagers, for secondary provision.",
        age_preference={"age_35_54": 1.0, "age_0_15": 0.7, "age_55_74": 0.3},
        tenure_preference={
            "owns_with_mortgage": 0.8,
            "owns_outright": 0.4,
            "social_rented": 0.4,
        },
        bed_range=_NA_BEDS,
    ),
    "young_adults_he": Segment(
        id="young_adults_he",
        industry="education",
        label="Young adults (HE and FE)",
        description="Students and young adults for higher and further education.",
        age_preference={"age_16_34": 1.0},
        tenure_preference={"private_rented": 1.0, "social_rented": 0.3},
        bed_range=_NA_BEDS,
    ),
    "adult_learners": Segment(
        id="adult_learners",
        industry="education",
        label="Adult learners",
        description="Adults for community, vocational and lifelong learning.",
        age_preference={"age_35_54": 1.0, "age_55_74": 0.6, "age_16_34": 0.5},
        tenure_preference={
            "owns_with_mortgage": 0.6,
            "private_rented": 0.5,
            "social_rented": 0.4,
        },
        bed_range=_NA_BEDS,
    ),
    # --- local authority / public sector -----------------------------------
    "families_households": Segment(
        id="families_households",
        industry="public_sector",
        label="Families and households",
        description="Households with children, for family-facing services.",
        age_preference={"age_35_54": 1.0, "age_0_15": 0.8},
        tenure_preference={
            "owns_with_mortgage": 0.7,
            "social_rented": 0.5,
            "private_rented": 0.5,
        },
        bed_range=_NA_BEDS,
    ),
    "working_age_residents": Segment(
        id="working_age_residents",
        industry="public_sector",
        label="Working age residents",
        description="Working age population for employment and general services.",
        age_preference={"age_35_54": 1.0, "age_16_34": 0.8},
        tenure_preference={
            "owns_with_mortgage": 0.6,
            "private_rented": 0.6,
            "social_rented": 0.4,
        },
        bed_range=_NA_BEDS,
    ),
    "older_residents": Segment(
        id="older_residents",
        industry="public_sector",
        label="Older residents",
        description="Older residents for adult social care and accessibility.",
        age_preference={"age_55_74": 1.0, "age_75_plus": 0.8},
        tenure_preference={"owns_outright": 0.8, "social_rented": 0.4},
        bed_range=_NA_BEDS,
    ),
    "deprivation_priority": Segment(
        id="deprivation_priority",
        industry="public_sector",
        label="Priority communities",
        description="Higher-need communities, proxied by social-rented tenure.",
        age_preference={"age_0_15": 0.6, "age_35_54": 0.6, "age_75_plus": 0.6},
        tenure_preference={"social_rented": 1.0, "private_rented": 0.5},
        bed_range=_NA_BEDS,
    ),
}


def list_segments(industry: str | None = None) -> list[dict]:
    """Plain dicts for the API and the form picker. Filtered to an industry when
    one is given (the brand's industry), else every segment across sectors."""
    return [
        {
            "id": s.id,
            "industry": s.industry,
            "label": s.label,
            "description": s.description,
            "bedRange": s.bed_range,
        }
        for s in SEGMENTS.values()
        if industry is None or s.industry == industry
    ]


def apply_segment(
    config: ScoringConfig,
    segment_id: str,
    *,
    override_bed_range: bool = True,
) -> ScoringConfig:
    """Return a config tuned for the segment.

    Always sets the age and tenure preference vectors (these drive the segment
    lens and are not otherwise exposed). The bed range is set from the segment
    only when override_bed_range is True, so an explicit bed range from the
    caller is preserved.
    """
    seg = SEGMENTS.get(segment_id)
    if seg is None:
        return config
    changes = {
        "age_preference": dict(seg.age_preference),
        "tenure_preference": dict(seg.tenure_preference),
        "segment": seg.id,
    }
    if override_bed_range:
        changes["bed_range"] = seg.bed_range
    return replace(config, **changes)
