"""Stage 6: assemble the Battlecard payload for one area.

Builds the single structured payload that renders to four surfaces (web drawer,
PDF, PPTX, KML balloon). Commentary is templated from the signals, not free
written, so output is consistent and auditable (SCOPING.md Section 7, step 6).
Phase 2 may add an LLM pass to sharpen prose behind a review gate.

Generated prose follows the house conventions: no em dashes, no Oxford commas,
no markdown headers. ONS suppression flows through as null DataValues, never
zero, so the render can surface confidence rather than hide gaps.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..context_metrics import build_context_metrics
from ..scoring.profile import AreaProfile, ScoringConfig
from ..scoring.score import ScoreBreakdown
from .schema import (
    BATTLECARD_SCHEMA_VERSION,
    AddressableSegments,
    AgeBand,
    AudienceAndDemographics,
    AudienceCommentary,
    AudienceMessage,
    Battlecard,
    BattlecardCharts,
    BattlecardHeader,
    CatchmentContext,
    CohortCommentary,
    ContextMetric,
    DataConfidence,
    DataValue,
    IncomeAndTenure,
    IncomeChart,
    KeyStatistics,
    LaCallout,
    PricingRationale,
    ScoreBreakdownModel,
    ScoreContribution,
    TenureChart,
    VisualSummary,
)

# Maps the internal snake_case signal names to the camelCase contract names.
_SIGNAL_TO_CONTRACT = {
    "income_fit": "incomeFit",
    "tenure_signal": "tenureSignal",
    "age_skew": "ageSkew",
    "addressable_scale": "addressableScale",
    "household_type": "householdType",
    # Objective signals.
    "income_level": "incomeLevel",
    "low_deprivation": "lowDeprivation",
    "green_space": "greenSpace",
    "schools": "schools",
    "low_crime": "lowCrime",
    "healthcare_access": "healthcareAccess",
    "lookalike": "lookalike",
    "land_supply": "landSupply",
}

_AGE_BANDS = [
    ("0 to 15", "age_0_15"),
    ("16 to 34", "age_16_34"),
    ("35 to 54", "age_35_54"),
    ("55 to 74", "age_55_74"),
    ("75 plus", "age_75_plus"),
]


@dataclass(frozen=True)
class DevelopmentInfo:
    """The development-level inputs the Battlecard header carries."""

    development_name: str
    town: str
    postcode: str | None
    strapline: str
    lifestyle_pillars: list[str]
    development_features: list[str]


@dataclass(frozen=True)
class IncomeContext:
    """Catchment-wide income range for the income chart callouts."""

    lowest_la_name: str
    lowest_la_value: float | None
    highest_la_name: str
    highest_la_value: float | None


@dataclass(frozen=True)
class CatchmentStats:
    """Catchment-wide aggregates so an area can be shown relative to the whole."""

    # Population-weighted mean of area mean incomes across the catchment.
    mean_income: float | None
    # Total population inside the catchment, summed across areas.
    total_population_inside: float | None


def _dv(value: float | None) -> DataValue:
    """Wrap a value, marking it suppressed when missing."""
    if value is None:
        return DataValue(value=None, suppressed=True)
    return DataValue(value=value)


def _pct(share: float | None) -> float | None:
    """Convert a 0..1 share to a percentage, preserving None."""
    return None if share is None else round(share * 100, 1)


def _owner_occupied_pct(profile: AreaProfile) -> float | None:
    outright = profile.tenure.owns_outright
    mortgage = profile.tenure.owns_with_mortgage
    if outright is None and mortgage is None:
        return None
    return round(((outright or 0.0) + (mortgage or 0.0)) * 100, 1)


def _inside(value: float | None, proportion: float) -> float | None:
    """Scale a whole-area count to the part inside the catchment."""
    return None if value is None else value * proportion


def _key_statistics(profile: AreaProfile, config: ScoringConfig) -> KeyStatistics:
    pop_inside = _inside(profile.population, profile.proportion_inside)
    hh_inside = _inside(profile.households, profile.proportion_inside)
    return KeyStatistics(
        bed_range=config.bed_range,
        average_household_income=_dv(profile.mean_income),
        owner_occupied_percentage=_dv(_owner_occupied_pct(profile)),
        price_from=_dv(config.price_band.frm),
        median_age=_dv(profile.median_age),
        population_catchment=_dv(None if pop_inside is None else round(pop_inside)),
        households_catchment=_dv(None if hh_inside is None else round(hh_inside)),
        family_household_share=_dv(_pct(profile.family_household_share)),
        median_house_price=_dv(profile.median_house_price),
    )


def _age_chart(profile: AreaProfile) -> list[AgeBand]:
    bands: list[AgeBand] = []
    for label, attr in _AGE_BANDS:
        share = getattr(profile.age, attr)
        count = (
            None
            if (share is None or profile.population is None)
            else round(share * profile.population)
        )
        bands.append(
            AgeBand(label=label, count=_dv(count), percentage=_dv(_pct(share)))
        )
    return bands


def _income_chart(profile: AreaProfile, context: IncomeContext) -> IncomeChart:
    return IncomeChart(
        mean=_dv(profile.mean_income),
        median=_dv(profile.median_income),
        lowest_la=LaCallout(
            name=context.lowest_la_name, value=_dv(context.lowest_la_value)
        ),
        highest_la=LaCallout(
            name=context.highest_la_name, value=_dv(context.highest_la_value)
        ),
    )


def _tenure_chart(profile: AreaProfile) -> TenureChart:
    return TenureChart(
        owns_outright=_dv(_pct(profile.tenure.owns_outright)),
        owns_with_mortgage=_dv(_pct(profile.tenure.owns_with_mortgage)),
        social_rented=_dv(_pct(profile.tenure.social_rented)),
        private_rented=_dv(_pct(profile.tenure.private_rented)),
    )


# --- Templated commentary -----------------------------------------------------


def _income_commentary(profile: AreaProfile) -> str:
    median, mean = profile.median_income, profile.mean_income
    if median is None or mean is None:
        return (
            "Income data for this area is incomplete, so positioning should be "
            "confirmed against neighbouring areas before pricing decisions."
        )
    spread = mean - median
    if spread > 0.15 * median:
        return (
            f"Mean household income of {mean:,.0f} sits well above the median of "
            f"{median:,.0f}, a long upper tail that supports a premium tier "
            "alongside the core offer."
        )
    return (
        f"Mean and median household incomes are close, at {mean:,.0f} and "
        f"{median:,.0f}, a narrow spread that argues for confident mid-market "
        "positioning rather than luxury."
    )


def _tenure_commentary(profile: AreaProfile) -> str:
    private = profile.tenure.private_rented
    outright = profile.tenure.owns_outright
    if private is None and outright is None:
        return (
            "Tenure data for this area is incomplete, so the buyer pipeline read "
            "should be treated as indicative."
        )
    parts: list[str] = []
    if private is not None and private >= 0.20:
        parts.append(
            f"A private rented share of {private * 100:.0f}% signals a healthy "
            "first-time buyer pipeline"
        )
    if outright is not None and outright >= 0.30:
        parts.append(
            f"outright ownership at {outright * 100:.0f}% points to downsizer "
            "potential"
        )
    if not parts:
        return (
            "The tenure mix is balanced, with no single signal dominating, so "
            "target a broad owner-occupier audience."
        )
    return ". ".join(p[0].upper() + p[1:] for p in parts) + "."


def _audience_messages(profile: AreaProfile) -> list[AudienceMessage]:
    """Derive audience tiers from the strongest tenure and age signals.

    Channels are left to the Phase 2 GWI persona enrichment, so they are
    omitted here rather than guessed.
    """
    messages: list[AudienceMessage] = []
    private = profile.tenure.private_rented or 0.0
    mortgage = profile.tenure.owns_with_mortgage or 0.0
    outright = profile.tenure.owns_outright or 0.0
    ranked = sorted(
        [
            ("First-time buyers", private, ["A first home within reach"]),
            ("Family second steppers", mortgage, ["Room to grow into"]),
            ("Downsizers", outright, ["A simpler home, same community"]),
        ],
        key=lambda item: item[1],
        reverse=True,
    )
    tiers = ("primary", "secondary", "tertiary")
    for tier, (audience, _share, lines) in zip(tiers, ranked, strict=True):
        messages.append(
            AudienceMessage(tier=tier, audience=audience, message_lines=lines)
        )
    return messages


def _audience_commentary(messages: list[AudienceMessage]) -> list[AudienceCommentary]:
    bodies = {
        "First-time buyers": (
            "This audience is rent-burdened and ready to buy, so lead with "
            "affordability, deposit support and the cost of staying put."
        ),
        "Family second steppers": (
            "Growing families trading up respond to space, schools and a settled "
            "community, so anchor the message in room to grow."
        ),
        "Downsizers": (
            "Outright owners releasing equity value low maintenance living and "
            "staying near friends, so speak to a simpler home without uprooting."
        ),
    }
    return [
        AudienceCommentary(
            tier=m.tier,
            audience=m.audience,
            body=bodies.get(m.audience, "Tailor the message to this audience."),
        )
        for m in messages
    ]


def _cohort_commentary(profile: AreaProfile) -> list[CohortCommentary]:
    cohorts: list[CohortCommentary] = []
    pairs = [
        ("16 to 34", profile.age.age_16_34, "a first-time buyer pipeline"),
        ("35 to 54", profile.age.age_35_54, "family second steppers"),
        ("55 to 74", profile.age.age_55_74, "downsizer potential"),
    ]
    for cohort, share, implication in pairs:
        if share is None:
            continue
        cohorts.append(
            CohortCommentary(
                cohort=cohort,
                body=(
                    f"The {cohort} cohort is {share * 100:.0f}% of the area, "
                    f"indicating {implication}."
                ),
            )
        )
    return cohorts


def _pricing_rationale(profile: AreaProfile, config: ScoringConfig) -> PricingRationale:
    """Implied affordable price from local income against the scheme price.

    Prefers median income, falling back to mean (ONS small-area income is mean
    only at MSOA level), so a present mean does not read as "incomplete".
    """
    income = profile.median_income
    income_label = "median income"
    if income is None:
        income = profile.mean_income
        income_label = "average income"
    mult = config.affordability_multiple
    price_from = config.price_band.frm
    implied = None if income is None else round(income * mult)

    if implied is None:
        positioning = (
            "Income data is incomplete here, so confirm pricing against "
            "neighbouring areas before setting the entry point."
        )
    elif price_from <= implied:
        positioning = (
            f"An {income_label} of £{income:,.0f} supports about £{implied:,.0f} at "
            f"{mult:g}x income. With homes from £{price_from:,.0f} the entry price is "
            "within local reach, so lead on attainability and first-time buyer support."
        )
    elif price_from <= implied * 1.2:
        positioning = (
            f"An {income_label} of £{income:,.0f} supports about £{implied:,.0f} at "
            f"{mult:g}x income. Homes from £{price_from:,.0f} are a modest stretch, so "
            "emphasise value, specification and purchase incentives."
        )
    else:
        positioning = (
            f"An {income_label} of £{income:,.0f} supports about £{implied:,.0f} at "
            f"{mult:g}x income. Homes from £{price_from:,.0f} sit above local means, so "
            "target equity-rich movers and in-migration rather than local first buyers."
        )

    # Local sales values anchor the scheme price for a land or site appraisal.
    hp = profile.median_house_price
    if hp:
        if price_from <= hp:
            positioning += (
                f" Local homes sell for around £{hp:,.0f}, so a price from "
                f"£{price_from:,.0f} is at or below prevailing values."
            )
        else:
            premium = (price_from / hp - 1) * 100
            positioning += (
                f" Local homes sell for around £{hp:,.0f}, so a price from "
                f"£{price_from:,.0f} is a {premium:.0f}% new-build premium to confirm "
                "against the specification and local comparables."
            )

    return PricingRationale(
        implied_affordable_price=_dv(implied),
        affordability_multiple=mult,
        price_from=_dv(price_from),
        positioning=positioning,
    )


def _addressable_segments(profile: AreaProfile) -> AddressableSegments:
    """Estimated household counts inside the catchment, by strategic segment."""
    hh_inside = _inside(profile.households, profile.proportion_inside)

    def segment(share: float | None) -> float | None:
        if hh_inside is None or share is None:
            return None
        return round(hh_inside * share)

    return AddressableSegments(
        first_time_buyer_pipeline=_dv(segment(profile.tenure.private_rented)),
        downsizer_pool=_dv(segment(profile.tenure.owns_outright)),
        family_households=_dv(segment(profile.family_household_share)),
    )


def _catchment_context(
    profile: AreaProfile, catchment: CatchmentStats
) -> CatchmentContext:
    """This area indexed against the catchment average."""
    income_index = None
    if profile.mean_income is not None and catchment.mean_income:
        income_index = round(profile.mean_income / catchment.mean_income * 100)

    share = None
    pop_inside = _inside(profile.population, profile.proportion_inside)
    if pop_inside is not None and catchment.total_population_inside:
        share = round(pop_inside / catchment.total_population_inside * 100, 1)

    return CatchmentContext(
        income_index=_dv(income_index),
        share_of_catchment_population=_dv(share),
    )


# Human labels for the inputs whose suppression we report. Income counts as
# present if either median or mean is available (ONS small-area income is mean
# only at MSOA level, so requiring median would flag every area).
_CONFIDENCE_FIELDS = {
    "income": lambda p: (
        p.median_income if p.median_income is not None else p.mean_income
    ),
    "population": lambda p: p.population,
    "households": lambda p: p.households,
    "tenure": lambda p: p.tenure.private_rented,
    "age profile": lambda p: p.age.age_35_54,
    "household type": lambda p: p.family_household_share,
}


def _data_confidence(profile: AreaProfile) -> DataConfidence:
    """Report which inputs were suppressed and an overall confidence level."""
    suppressed = [
        name for name, getter in _CONFIDENCE_FIELDS.items() if getter(profile) is None
    ]
    count = len(suppressed)
    if count == 0:
        level = "high"
        note = "All key inputs are present for this area."
    elif count <= 2:
        level = "medium"
        note = "Some inputs are suppressed by ONS, so read those signals with care."
    else:
        level = "low"
        note = "Several inputs are suppressed, so treat this area as indicative."
    return DataConfidence(level=level, suppressed_fields=suppressed, note=note)


def _score_model(score: ScoreBreakdown) -> ScoreBreakdownModel:
    return ScoreBreakdownModel(
        total=round(score.total, 4),
        band=score.band,
        # Only signals the chosen objective gives weight to appear in the
        # breakdown, so it stays readable rather than listing every signal in
        # the library with a zero weight.
        contributions=[
            ScoreContribution(
                signal=_SIGNAL_TO_CONTRACT[c.signal],
                weight=round(c.weight, 4),
                raw_score=round(c.raw_score, 4),
                contribution=round(c.contribution, 4),
                rationale=c.rationale,
            )
            for c in score.contributions
            if c.weight > 0
        ],
    )


def assemble_battlecard(
    profile: AreaProfile,
    config: ScoringConfig,
    score: ScoreBreakdown,
    rank: int,
    development: DevelopmentInfo,
    income_context: IncomeContext,
    catchment_stats: CatchmentStats | None = None,
) -> Battlecard:
    """Build the validated Battlecard payload for one scored area."""
    # When catchment aggregates are not supplied, context indices are null
    # rather than guessed.
    catchment_stats = catchment_stats or CatchmentStats(
        mean_income=None, total_population_inside=None
    )
    messages = _audience_messages(profile)
    objective_id = config.objective
    objective_label, highlight_keys = _objective_meta(objective_id)
    visual_summary = VisualSummary(
        header=BattlecardHeader(
            development_name=development.development_name,
            town=development.town,
            postcode=development.postcode,
            strapline=development.strapline,
            lifestyle_pillars=development.lifestyle_pillars,
        ),
        key_statistics=_key_statistics(profile, config),
        audience_messaging=messages,
        development_features=development.development_features,
        charts=BattlecardCharts(
            age_demographics=_age_chart(profile),
            household_income=_income_chart(profile, income_context),
            housing_tenure=_tenure_chart(profile),
        ),
    )

    return Battlecard(
        schema_version=BATTLECARD_SCHEMA_VERSION,
        area_code=profile.area_code,
        area_type=profile.area_type,
        proportion_inside=round(profile.proportion_inside, 4),
        rank=rank,
        score=_score_model(score),
        visual_summary=visual_summary,
        audience_and_demographics=AudienceAndDemographics(
            audience_tiers=_audience_commentary(messages),
            age_cohorts=_cohort_commentary(profile),
        ),
        income_and_tenure=IncomeAndTenure(
            income_commentary=_income_commentary(profile),
            tenure_commentary=_tenure_commentary(profile),
        ),
        pricing_rationale=_pricing_rationale(profile, config),
        addressable_segments=_addressable_segments(profile),
        catchment_context=_catchment_context(profile, catchment_stats),
        data_confidence=_data_confidence(profile),
        context_metrics=[
            ContextMetric(**row, highlight=row["key"] in highlight_keys)
            for row in build_context_metrics(profile.context)
        ],
        objective=objective_id,
        objective_label=objective_label,
    )


# Objective highlight signal keys to the context-metric keys they map to, so the
# objective's focus data points can be emphasised on the card.
_SIGNAL_TO_CONTEXT_KEY = {
    "low_deprivation": "imd_decile",
    "low_crime": "crime_per_1k",
    "green_space": "greenspace_minutes",
    "schools": "schools_good_pct",
    "healthcare_access": "hospital_km",
}


def _objective_meta(objective_id: str | None) -> tuple[str | None, set[str]]:
    """The objective's label and the context-metric keys it highlights."""
    if not objective_id:
        return None, set()
    from ..scoring.objectives import OBJECTIVES

    obj = OBJECTIVES.get(objective_id)
    if obj is None:
        return None, set()
    keys = {
        _SIGNAL_TO_CONTEXT_KEY[s] for s in obj.highlight if s in _SIGNAL_TO_CONTEXT_KEY
    }
    return obj.label, keys
