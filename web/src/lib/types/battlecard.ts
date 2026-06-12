// The Battlecard payload is the single source of truth for one area's output.
// It renders to four surfaces: the in-app drawer, PDF, PPTX and the KML balloon.
// Never fork this data per surface. See SCOPING.md Section 9 and design-framework.md.
//
// This module is the contract between the Python worker (which produces the
// payload) and the UI render (which consumes it). The worker mirrors these
// shapes with pydantic models and a shared JSON schema so all surfaces can
// trust the data. Keep the two in sync.

/** ONS area identifier. MSOA for MVP, LA reserved for Phase 2 (leisure). */
export type AreaType = "MSOA" | "LA";

/** Priority band, paired with rank and label so colour is never the only signal. */
export type PriorityBand = "high" | "mid" | "low";

/**
 * A value that may be suppressed or unavailable in the ONS source. A suppressed
 * cell is null, not zero (house-standards.md, data handling). `confidence`
 * surfaces data quality in the deep-dive rather than hiding gaps.
 */
export interface DataValue<T = number> {
  value: T | null;
  /** True when the source cell was suppressed or rounded by ONS. */
  suppressed?: boolean;
  confidence?: "high" | "medium" | "low";
}

// --- Page 1: visual summary ---------------------------------------------------

export interface BattlecardHeader {
  developmentName: string;
  town: string;
  /** Input postcode, or null for grid-ref-only sites with no postcode yet. */
  postcode: string | null;
  strapline: string;
  lifestylePillars: string[];
}

export interface KeyStatistics {
  bedRange: string;
  averageHouseholdIncome: DataValue;
  ownerOccupiedPercentage: DataValue;
  priceFrom: DataValue;
  medianAge: DataValue;
  /** Addressable population inside the catchment for this area. */
  populationCatchment: DataValue;
  /** Households inside the catchment for this area. */
  householdsCatchment: DataValue;
  /** Share of households that are one-family households, as a percentage. */
  familyHouseholdShare: DataValue;
  /** Local median house price (ONS HPSSA). */
  medianHousePrice: DataValue;
}

export type AudienceTier = "primary" | "secondary" | "tertiary";

export interface AudienceMessage {
  tier: AudienceTier;
  audience: string;
  messageLines: string[];
  /** Channel mix for this tier, informed by GWI personas (Phase 2 enrichment). */
  channels?: string[];
}

// --- Charts (Page 1). Banded so labels and values travel with the colour. ----

export interface AgeBand {
  /** "0 to 15", "16 to 34", "35 to 54", "55 to 74", "75 plus". */
  label: string;
  count: DataValue;
  percentage: DataValue;
}

export interface IncomeChart {
  mean: DataValue;
  median: DataValue;
  lowestLa: { name: string; value: DataValue };
  highestLa: { name: string; value: DataValue };
}

export interface TenureChart {
  ownsOutright: DataValue;
  ownsWithMortgage: DataValue;
  socialRented: DataValue;
  privateRented: DataValue;
}

export interface BattlecardCharts {
  ageDemographics: AgeBand[];
  householdIncome: IncomeChart;
  housingTenure: TenureChart;
}

export interface VisualSummary {
  header: BattlecardHeader;
  keyStatistics: KeyStatistics;
  audienceMessaging: AudienceMessage[];
  /** "The development and location" feature bullets. */
  developmentFeatures: string[];
  charts: BattlecardCharts;
}

// --- Pages 2 and 3: commentary ------------------------------------------------
// Commentary is templated from the signals, not free-written, so output is
// consistent and auditable (SCOPING.md Section 7, step 6). Prose follows the
// output conventions: no em dashes, no Oxford commas, no markdown headers.

export interface AudienceCommentary {
  tier: AudienceTier;
  audience: string;
  body: string;
}

export interface CohortCommentary {
  /** Age cohort label, matching the age band labels. */
  cohort: string;
  body: string;
}

/** Page 2: audience messaging overview and demographic commentary. */
export interface AudienceAndDemographics {
  audienceTiers: AudienceCommentary[];
  ageCohorts: CohortCommentary[];
}

/** Page 3: household income and tenure commentary with positioning implications. */
export interface IncomeAndTenure {
  incomeCommentary: string;
  tenureCommentary: string;
}

// --- Scoring provenance -------------------------------------------------------
// Every ranking must be reproducible and explainable from stored config and
// data (SCOPING.md Section 8 and 12). The deep-dive shows why an area scored
// as it did, so the contributing signals travel with the payload.

export interface ScoreContribution {
  signal:
    | "incomeFit"
    | "tenureSignal"
    | "ageSkew"
    | "addressableScale"
    | "householdType"
    | "incomeLevel"
    | "lowDeprivation"
    | "greenSpace"
    | "schools"
    | "lowCrime"
    | "healthcareAccess";
  weight: number;
  /** Normalised 0 to 1 score for this signal before weighting. */
  rawScore: number;
  /** weight * rawScore, the signal's contribution to the total. */
  contribution: number;
  /** Plain-language reason, e.g. why income fit scored as it did. */
  rationale: string;
}

export interface ScoreBreakdown {
  total: number;
  band: PriorityBand;
  contributions: ScoreContribution[];
}

// --- Data-driven sections beyond the Abbots Vale reference --------------------
// Derived from the same ONS inputs, reproducible, no extra data sources.

/** Implied affordability against the scheme price, with a positioning stance. */
export interface PricingRationale {
  impliedAffordablePrice: DataValue;
  affordabilityMultiple: number;
  priceFrom: DataValue;
  positioning: string;
}

/** Estimated household counts inside the catchment, by strategic segment. */
export interface AddressableSegments {
  firstTimeBuyerPipeline: DataValue;
  downsizerPool: DataValue;
  familyHouseholds: DataValue;
}

/** This area relative to the whole catchment, so the rank has a reason. */
export interface CatchmentContext {
  /** 100 means the catchment average; above is richer, below is poorer. */
  incomeIndex: DataValue;
  shareOfCatchmentPopulation: DataValue;
}

/** Explicit data quality, surfaced rather than hidden. */
export interface DataConfidence {
  level: "high" | "medium" | "low";
  suppressedFields: string[];
  note: string;
}

// --- The full payload ---------------------------------------------------------

export interface Battlecard {
  /** Schema version so stored payloads can be migrated and validated. */
  schemaVersion: string;
  areaCode: string;
  areaType: AreaType;
  /** Proportion of the area inside the drive-time isochrone, 0 to 1. */
  proportionInside: number;
  rank: number;
  score: ScoreBreakdown;
  visualSummary: VisualSummary;
  audienceAndDemographics: AudienceAndDemographics;
  incomeAndTenure: IncomeAndTenure;
  pricingRationale: PricingRationale;
  addressableSegments: AddressableSegments;
  catchmentContext: CatchmentContext;
  dataConfidence: DataConfidence;
  /** Additional public data points (green space, deprivation, crime) for context. */
  contextMetrics?: ContextMetric[];
}

export interface ContextMetric {
  key: string;
  label: string;
  value: number;
  unit: string;
  direction?: string;
}

/** Current Battlecard schema version. Bump on any breaking shape change. */
export const BATTLECARD_SCHEMA_VERSION = "1.0.0";
