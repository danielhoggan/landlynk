"""Pure scoring functions.

Each function takes an :class:`AreaProfile` and a :class:`ScoringConfig` and
returns a raw signal score in 0..1, with a plain-language rationale. The blended
priority score is a transparent weighted sum, so any ranking is reproducible and
explainable from stored config and data (SCOPING.md Section 8, Section 12).

Suppressed inputs (None) are handled explicitly. A signal with no usable data
returns a neutral 0.0 raw score and says so in the rationale, rather than
coercing missing data to a value.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .profile import AreaProfile, ScoringConfig

SignalName = str


@dataclass(frozen=True)
class SignalScore:
    signal: SignalName
    raw_score: float  # 0..1 before weighting
    rationale: str


@dataclass(frozen=True)
class Contribution:
    signal: SignalName
    weight: float
    raw_score: float
    contribution: float  # weight * raw_score
    rationale: str


@dataclass(frozen=True)
class ScoreBreakdown:
    total: float  # 0..1
    band: str  # "high" | "mid" | "low"
    contributions: list[Contribution]


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def score_income_fit(profile: AreaProfile, config: ScoringConfig) -> SignalScore:
    """Reward alignment between area income and the price band, not raw wealth.

    The Abbots Vale logic is the model: a narrow income spread argues for
    mid-market positioning, not luxury. Fit is highest when the area's income is
    close to the income the product price implies. Prefers median income, and
    falls back to mean when median is unavailable (ONS small-area income is often
    mean only at MSOA level).
    """
    income = profile.median_income
    income_label = "Median income"
    if income is None:
        income = profile.mean_income
        income_label = "Mean income"
    if income is None:
        return SignalScore("income_fit", 0.0, "Income suppressed, no income fit signal")

    target = config.price_band.midpoint / config.affordability_multiple
    if target <= 0:
        return SignalScore(
            "income_fit", 0.0, "Invalid price band, cannot compute income fit"
        )

    relative_gap = abs(income - target) / target
    raw = _clamp01(1.0 - relative_gap)
    return SignalScore(
        "income_fit",
        raw,
        (
            f"{income_label} {income:,.0f} against an implied target of "
            f"{target:,.0f}, a {relative_gap * 100:.0f}% gap"
        ),
    )


def _weighted_share(
    shares: dict[str, float | None], preference: dict[str, float]
) -> tuple[float, bool]:
    """Dot product of available shares with preference weights, renormalised.

    Returns the score in 0..1 and whether any data was usable. Suppressed
    components are dropped and the preference renormalised over what remains.
    """
    usable = {
        k: v for k, v in shares.items() if v is not None and preference.get(k, 0) >= 0
    }
    if not usable:
        return 0.0, False
    pref_total = sum(preference.get(k, 0.0) for k in usable)
    if pref_total <= 0:
        return 0.0, True
    score = sum(usable[k] * preference.get(k, 0.0) for k in usable) / pref_total
    return _clamp01(score), True


def score_tenure_signal(profile: AreaProfile, config: ScoringConfig) -> SignalScore:
    """Weight the area's tenure mix against the product's target tenures.

    Private rented indicates a first-time buyer pipeline, outright ownership a
    downsizer pool, mortgaged ownership second-stepper progression.
    """
    shares = {
        "owns_outright": profile.tenure.owns_outright,
        "owns_with_mortgage": profile.tenure.owns_with_mortgage,
        "social_rented": profile.tenure.social_rented,
        "private_rented": profile.tenure.private_rented,
    }
    raw, usable = _weighted_share(shares, config.tenure_preference)
    if not usable:
        return SignalScore(
            "tenure_signal", 0.0, "Tenure data suppressed, no tenure signal"
        )
    return SignalScore(
        "tenure_signal",
        raw,
        f"Tenure mix aligns {raw * 100:.0f}% with the product's target tenures",
    )


def score_age_skew(profile: AreaProfile, config: ScoringConfig) -> SignalScore:
    """Match the area's age profile to the product's target cohorts."""
    shares = {
        "age_0_15": profile.age.age_0_15,
        "age_16_34": profile.age.age_16_34,
        "age_35_54": profile.age.age_35_54,
        "age_55_74": profile.age.age_55_74,
        "age_75_plus": profile.age.age_75_plus,
    }
    raw, usable = _weighted_share(shares, config.age_preference)
    if not usable:
        return SignalScore("age_skew", 0.0, "Age data suppressed, no age signal")
    return SignalScore(
        "age_skew",
        raw,
        f"Age profile aligns {raw * 100:.0f}% with the product's target cohorts",
    )


def score_addressable_scale(profile: AreaProfile, config: ScoringConfig) -> SignalScore:
    """Population inside the catchment, weighted by the proportion inside.

    A saturating curve so very large areas do not dominate purely on headcount.
    """
    if profile.population is None:
        return SignalScore(
            "addressable_scale", 0.0, "Population suppressed, no scale signal"
        )
    inside = profile.population * profile.proportion_inside
    raw = _clamp01(1.0 - math.exp(-inside / config.scale_saturation))
    return SignalScore(
        "addressable_scale",
        raw,
        f"About {inside:,.0f} people inside the catchment from this area",
    )


def score_household_type(profile: AreaProfile, config: ScoringConfig) -> SignalScore:
    """Match family composition to the bed range and product mix.

    A family-oriented bed range rewards a higher family household share. A
    compact or downsizer range inverts the preference.
    """
    if profile.family_household_share is None:
        return SignalScore(
            "household_type", 0.0, "Household type suppressed, no signal"
        )
    family_oriented = _bed_range_is_family(config.bed_range)
    raw = (
        profile.family_household_share
        if family_oriented
        else 1.0 - profile.family_household_share
    )
    raw = _clamp01(raw)
    orientation = "family" if family_oriented else "non-family"
    return SignalScore(
        "household_type",
        raw,
        (
            f"Family households are {profile.family_household_share * 100:.0f}% of the area, "
            f"scored for a {orientation} product mix"
        ),
    )


def _bed_range_is_family(bed_range: str) -> bool:
    """A bed range that includes 3 or more beds is treated as family-oriented."""
    digits = [int(c) for c in bed_range if c.isdigit()]
    return bool(digits) and max(digits) >= 3


# --- objective signals -------------------------------------------------------
# These extend the home-sales signals above so the same engine can serve other
# objectives (wealth targeting, retail siting, amenity-led). They draw on the
# public data points loaded as area context (green space, deprivation, crime,
# schools, hospital access) and on raw income. Each is pure and explainable, and
# returns a neutral 0.0 with a clear rationale when its data is unavailable. They
# only affect a score when an objective gives them weight; default weight is 0.


def _context(profile: AreaProfile, key: str) -> float | None:
    value = profile.context.get(key)
    return float(value) if value is not None else None


def score_income_level(profile: AreaProfile, config: ScoringConfig) -> SignalScore:
    """Raw affluence: higher household income scores higher (saturating).

    Unlike income_fit, this rewards wealth itself, for objectives such as high
    net worth targeting where the richest areas are the goal.
    """
    income = profile.median_income or profile.mean_income
    if income is None:
        return SignalScore("income_level", 0.0, "Income suppressed, no affluence signal")
    raw = _clamp01(1.0 - math.exp(-income / 40_000.0))
    return SignalScore(
        "income_level", raw, f"Household income about {income:,.0f}"
    )


def score_low_deprivation(profile: AreaProfile, config: ScoringConfig) -> SignalScore:
    """Less deprived areas score higher, from the IMD decile (10 = least deprived)."""
    decile = _context(profile, "imd_decile")
    if decile is None:
        return SignalScore("low_deprivation", 0.0, "No deprivation data for this area")
    raw = _clamp01(decile / 10.0)
    return SignalScore(
        "low_deprivation", raw, f"IMD decile {decile:.0f} of 10 (10 = least deprived)"
    )


def score_green_space(profile: AreaProfile, config: ScoringConfig) -> SignalScore:
    """Closer green space scores higher, from walk minutes to the nearest park."""
    minutes = _context(profile, "greenspace_minutes")
    if minutes is None:
        return SignalScore("green_space", 0.0, "No green space data for this area")
    raw = _clamp01(1.0 - minutes / 30.0)
    return SignalScore(
        "green_space", raw, f"About {minutes:.0f} min walk to green space"
    )


def score_schools(profile: AreaProfile, config: ScoringConfig) -> SignalScore:
    """Share of schools rated Good or Outstanding scores higher."""
    pct = _context(profile, "schools_good_pct")
    if pct is None:
        return SignalScore("schools", 0.0, "No school rating data for this area")
    raw = _clamp01(pct / 100.0)
    return SignalScore("schools", raw, f"{pct:.0f}% of schools Good or Outstanding")


def score_low_crime(profile: AreaProfile, config: ScoringConfig) -> SignalScore:
    """Lower recorded crime per 1,000 residents scores higher."""
    crime = _context(profile, "crime_per_1k")
    if crime is None:
        return SignalScore("low_crime", 0.0, "No crime data for this area")
    raw = _clamp01(1.0 - crime / 200.0)
    return SignalScore("low_crime", raw, f"About {crime:.0f} crimes per 1,000 residents")


def score_healthcare_access(profile: AreaProfile, config: ScoringConfig) -> SignalScore:
    """Closer to a hospital scores higher, from distance in km."""
    km = _context(profile, "hospital_km")
    if km is None:
        return SignalScore("healthcare_access", 0.0, "No hospital distance for this area")
    raw = _clamp01(1.0 - km / 20.0)
    return SignalScore("healthcare_access", raw, f"About {km:.0f} km to the nearest hospital")


def feature_vector(profile: AreaProfile) -> dict[str, float]:
    """A small, comparable 0..1-ish feature vector for lookalike similarity.

    Only features with data are included, so areas with suppressed cells still
    compare on what they share. Income is scaled to a sensible ceiling.
    """
    v: dict[str, float] = {}
    income = profile.median_income or profile.mean_income
    if income is not None:
        v["income"] = _clamp01(income / 100_000.0)
    if profile.median_age is not None:
        v["median_age"] = _clamp01(profile.median_age / 100.0)
    if profile.family_household_share is not None:
        v["family"] = _clamp01(profile.family_household_share)
    if profile.tenure.owns_outright is not None:
        v["owns_outright"] = _clamp01(profile.tenure.owns_outright)
    if profile.tenure.private_rented is not None:
        v["private_rented"] = _clamp01(profile.tenure.private_rented)
    imd = profile.context.get("imd_decile")
    if imd is not None:
        v["imd_decile"] = _clamp01(float(imd) / 10.0)
    return v


def mean_feature_vector(profiles: list[AreaProfile]) -> dict[str, float]:
    """Mean of per-area feature vectors, averaging each feature over the areas
    that have it. The reference point for the lookalike signal."""
    sums: dict[str, float] = {}
    counts: dict[str, int] = {}
    for p in profiles:
        for k, val in feature_vector(p).items():
            sums[k] = sums.get(k, 0.0) + val
            counts[k] = counts.get(k, 0) + 1
    return {k: sums[k] / counts[k] for k in sums}


def score_lookalike(profile: AreaProfile, config: ScoringConfig) -> SignalScore:
    """Similarity of this area to the brand's best locations (0..1).

    Compares the area's feature vector to the reference (mean of the brand's
    target areas) on the features they share, as 1 minus the RMS distance.
    Neutral 0.0 when there is no reference or no shared feature.
    """
    reference = config.lookalike_reference
    if not reference:
        return SignalScore("lookalike", 0.0, "No best locations set, no lookalike signal")
    vector = feature_vector(profile)
    common = [k for k in reference if k in vector]
    if not common:
        return SignalScore("lookalike", 0.0, "No comparable data for a lookalike match")
    distance = math.sqrt(
        sum((vector[k] - reference[k]) ** 2 for k in common) / len(common)
    )
    raw = _clamp01(1.0 - distance)
    return SignalScore(
        "lookalike",
        raw,
        f"{raw * 100:.0f}% similar to the brand's best locations",
    )


def band_for_score(total: float) -> str:
    """Map a 0..1 score to a priority band. Thresholds match the UI helper."""
    if total >= 0.66:
        return "high"
    if total >= 0.33:
        return "mid"
    return "low"


def relative_band(rank: int, total: int) -> str:
    """Band an area by its rank within the catchment, in thirds.

    Priority is inherently relative: the job is to show where to focus first.
    Absolute score thresholds leave every area the same colour when scores
    cluster, so we split the ranked areas into a high, mid and low third. This
    guarantees a usable spread of colours on the map.
    """
    import math

    if total <= 0:
        return "low"
    if rank <= math.ceil(total / 3):
        return "high"
    if rank <= math.ceil(2 * total / 3):
        return "mid"
    return "low"


SCORERS = (
    ("income_fit", score_income_fit),
    ("tenure_signal", score_tenure_signal),
    ("age_skew", score_age_skew),
    ("addressable_scale", score_addressable_scale),
    ("household_type", score_household_type),
    # Objective signals (default weight 0; weighted by the chosen objective).
    ("income_level", score_income_level),
    ("low_deprivation", score_low_deprivation),
    ("green_space", score_green_space),
    ("schools", score_schools),
    ("low_crime", score_low_crime),
    ("healthcare_access", score_healthcare_access),
    ("lookalike", score_lookalike),
)


def compute_score(profile: AreaProfile, config: ScoringConfig) -> ScoreBreakdown:
    """Blend the signals into a transparent, reproducible priority score.

    Weights are normalised so they need not sum to 1 in config. The result
    carries every signal's contribution and rationale for the deep-dive.
    """
    weight_total = sum(config.weights.values())
    if weight_total <= 0:
        raise ValueError("Scoring weights must sum to a positive value")

    contributions: list[Contribution] = []
    total = 0.0
    for name, scorer in SCORERS:
        signal = scorer(profile, config)
        weight = config.weights.get(name, 0.0) / weight_total
        contribution = weight * signal.raw_score
        total += contribution
        contributions.append(
            Contribution(
                signal=name,
                weight=weight,
                raw_score=signal.raw_score,
                contribution=contribution,
                rationale=signal.rationale,
            )
        )

    total = _clamp01(total)
    return ScoreBreakdown(
        total=total, band=band_for_score(total), contributions=contributions
    )
