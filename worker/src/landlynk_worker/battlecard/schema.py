"""Pydantic models for the Battlecard payload.

These mirror the TypeScript contract in ``web/src/lib/types/battlecard.ts``.
The Battlecard is one structured payload per area that renders to four surfaces
(web drawer, PDF, PPTX, KML balloon). Validating here means all surfaces can
trust the data (house-standards.md, testing). Keep these in sync with the TS
types; both carry the same schema version.

Output prose in the commentary fields follows the house conventions: no em
dashes, no Oxford commas, no markdown headers.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

BATTLECARD_SCHEMA_VERSION = "1.0.0"

AreaType = Literal["MSOA", "LA"]
PriorityBand = Literal["high", "mid", "low"]
AudienceTier = Literal["primary", "secondary", "tertiary"]
Confidence = Literal["high", "medium", "low"]


class DataValue(BaseModel):
    """A value that may be suppressed. Null is not zero."""

    value: float | None = None
    suppressed: bool | None = None
    confidence: Confidence | None = None


class BattlecardHeader(BaseModel):
    development_name: str = Field(alias="developmentName")
    town: str
    postcode: str | None = None
    strapline: str
    lifestyle_pillars: list[str] = Field(alias="lifestylePillars")

    model_config = {"populate_by_name": True}


class KeyStatistics(BaseModel):
    bed_range: str = Field(alias="bedRange")
    average_household_income: DataValue = Field(alias="averageHouseholdIncome")
    owner_occupied_percentage: DataValue = Field(alias="ownerOccupiedPercentage")
    price_from: DataValue = Field(alias="priceFrom")
    median_age: DataValue = Field(alias="medianAge")
    population_catchment: DataValue = Field(alias="populationCatchment")
    households_catchment: DataValue = Field(alias="householdsCatchment")
    family_household_share: DataValue = Field(alias="familyHouseholdShare")
    median_house_price: DataValue = Field(alias="medianHousePrice")

    model_config = {"populate_by_name": True}


class AudienceMessage(BaseModel):
    tier: AudienceTier
    audience: str
    message_lines: list[str] = Field(alias="messageLines")
    channels: list[str] | None = None

    model_config = {"populate_by_name": True}


class AgeBand(BaseModel):
    label: str
    count: DataValue
    percentage: DataValue


class LaCallout(BaseModel):
    name: str
    value: DataValue


class IncomeChart(BaseModel):
    mean: DataValue
    median: DataValue
    lowest_la: LaCallout = Field(alias="lowestLa")
    highest_la: LaCallout = Field(alias="highestLa")

    model_config = {"populate_by_name": True}


class TenureChart(BaseModel):
    owns_outright: DataValue = Field(alias="ownsOutright")
    owns_with_mortgage: DataValue = Field(alias="ownsWithMortgage")
    social_rented: DataValue = Field(alias="socialRented")
    private_rented: DataValue = Field(alias="privateRented")

    model_config = {"populate_by_name": True}


class BattlecardCharts(BaseModel):
    age_demographics: list[AgeBand] = Field(alias="ageDemographics")
    household_income: IncomeChart = Field(alias="householdIncome")
    housing_tenure: TenureChart = Field(alias="housingTenure")

    model_config = {"populate_by_name": True}


class VisualSummary(BaseModel):
    header: BattlecardHeader
    key_statistics: KeyStatistics = Field(alias="keyStatistics")
    audience_messaging: list[AudienceMessage] = Field(alias="audienceMessaging")
    development_features: list[str] = Field(alias="developmentFeatures")
    charts: BattlecardCharts

    model_config = {"populate_by_name": True}


class AudienceCommentary(BaseModel):
    tier: AudienceTier
    audience: str
    body: str


class CohortCommentary(BaseModel):
    cohort: str
    body: str


class AudienceAndDemographics(BaseModel):
    audience_tiers: list[AudienceCommentary] = Field(alias="audienceTiers")
    age_cohorts: list[CohortCommentary] = Field(alias="ageCohorts")

    model_config = {"populate_by_name": True}


class IncomeAndTenure(BaseModel):
    income_commentary: str = Field(alias="incomeCommentary")
    tenure_commentary: str = Field(alias="tenureCommentary")

    model_config = {"populate_by_name": True}


class ScoreContribution(BaseModel):
    signal: Literal[
        "incomeFit", "tenureSignal", "ageSkew", "addressableScale", "householdType"
    ]
    weight: float
    raw_score: float = Field(alias="rawScore")
    contribution: float
    rationale: str

    model_config = {"populate_by_name": True}


class ScoreBreakdownModel(BaseModel):
    total: float
    band: PriorityBand
    contributions: list[ScoreContribution]


# --- Data-driven sections beyond the Abbots Vale reference --------------------
# These are derived from the same ONS inputs and are reproducible. They extend
# the reference card with pricing rationale, addressable segment sizes,
# catchment-relative context and explicit data confidence.


class PricingRationale(BaseModel):
    """Implied affordability against the scheme price, with a positioning stance."""

    implied_affordable_price: DataValue = Field(alias="impliedAffordablePrice")
    affordability_multiple: float = Field(alias="affordabilityMultiple")
    price_from: DataValue = Field(alias="priceFrom")
    positioning: str

    model_config = {"populate_by_name": True}


class AddressableSegments(BaseModel):
    """Estimated household counts inside the catchment, by strategic segment."""

    first_time_buyer_pipeline: DataValue = Field(alias="firstTimeBuyerPipeline")
    downsizer_pool: DataValue = Field(alias="downsizerPool")
    family_households: DataValue = Field(alias="familyHouseholds")

    model_config = {"populate_by_name": True}


class CatchmentContext(BaseModel):
    """This area relative to the whole catchment, so the rank has a reason."""

    # 100 means the catchment average; above is richer, below is poorer.
    income_index: DataValue = Field(alias="incomeIndex")
    share_of_catchment_population: DataValue = Field(alias="shareOfCatchmentPopulation")

    model_config = {"populate_by_name": True}


class DataConfidence(BaseModel):
    """Explicit data quality. Surfaced, not hidden (house-standards.md)."""

    level: Confidence
    suppressed_fields: list[str] = Field(alias="suppressedFields")
    note: str

    model_config = {"populate_by_name": True}


class Battlecard(BaseModel):
    schema_version: str = Field(
        default=BATTLECARD_SCHEMA_VERSION, alias="schemaVersion"
    )
    area_code: str = Field(alias="areaCode")
    area_type: AreaType = Field(alias="areaType")
    proportion_inside: float = Field(alias="proportionInside")
    rank: int
    score: ScoreBreakdownModel
    visual_summary: VisualSummary = Field(alias="visualSummary")
    audience_and_demographics: AudienceAndDemographics = Field(
        alias="audienceAndDemographics"
    )
    income_and_tenure: IncomeAndTenure = Field(alias="incomeAndTenure")
    pricing_rationale: PricingRationale = Field(alias="pricingRationale")
    addressable_segments: AddressableSegments = Field(alias="addressableSegments")
    catchment_context: CatchmentContext = Field(alias="catchmentContext")
    data_confidence: DataConfidence = Field(alias="dataConfidence")

    model_config = {"populate_by_name": True}
