// Catchment and area types. The map and ranking consume these; the worker
// produces them. See SCOPING.md Section 6 (data model) and Section 8 (scoring).

import type { AreaType, PriorityBand } from "./battlecard";

export type InputKind = "postcode" | "gridref";

export type JobStatus =
  | "queued"
  | "geocoding"
  | "isochrone"
  | "intersecting"
  | "joining"
  | "scoring"
  | "assembling"
  | "complete"
  | "failed";

/** WGS84 coordinate. The pipeline geocodes every input to this. */
export interface Coordinate {
  lat: number;
  lng: number;
}

/** The scoring config is stored with the catchment so any ranking is reproducible. */
export interface ScoringConfig {
  /** Weights per signal, summing to 1. Tuned per project. */
  weights: {
    incomeFit: number;
    tenureSignal: number;
    ageSkew: number;
    addressableScale: number;
    householdType: number;
  };
  /** Development price band the income fit is scored against. */
  priceBand: { from: number; to: number };
  bedRange: string;
  /** Minimum area overlap with the isochrone to retain it, 0 to 1. */
  overlapThreshold: number;
  driveTimeMinutes: number;
  /** Gross household income multiple used to imply an affordable price. */
  affordabilityMultiple: number;
}

export interface CatchmentInput {
  kind: InputKind;
  /** Raw postcode or OS grid reference as entered. */
  value: string;
  developmentName: string;
  /** Stored config (snake_case from the worker). Absent on older runs. */
  config?: StoredConfig | null;
}

/** The scoring config as stored and returned by the worker (snake_case keys). */
export interface StoredConfig {
  weights?: Record<string, number>;
  priceBand?: { from: number; to: number };
  bedRange?: string;
  overlapThreshold?: number;
  driveTimeMinutes?: number;
  catchmentMode?: string;
  radiusKm?: number;
  segment?: string;
  objective?: string;
  brandHeading?: string;
  brandSecondary?: string;
  brandAccent?: string;
  brandLogoPath?: string;
  affordabilityMultiple?: number;
}

/** GeoJSON geometry, kept loose here. PostGIS is the source of truth. */
export type GeoJsonGeometry = {
  type: string;
  coordinates: unknown;
};

/** Compact per-area metrics for map tooltips and signal filtering. */
export interface AreaMetrics {
  income: number | null;
  housePrice: number | null;
  ownerOccupied: number | null;
  medianAge: number | null;
  familyShare: number | null;
  privateRented: number | null;
  ownsOutright: number | null;
  incomeIndex: number | null;
}

/** A scored, ranked area inside the catchment. Drives the map and ranking list. */
export interface CatchmentArea {
  areaCode: string;
  areaType: AreaType;
  name: string;
  proportionInside: number;
  score: number;
  band: PriorityBand;
  rank: number;
  geometry: GeoJsonGeometry;
  metrics?: AreaMetrics | null;
}

/** Summary row for the history list. */
export interface CatchmentSummary {
  id: string;
  developmentName: string;
  inputValue: string;
  status: JobStatus;
  areaCount: number;
  createdAt: string | null;
  /** Owner email. Null for legacy runs created before ownership existed. */
  owner?: string | null;
  /** True when shared with the viewer by someone else (not their own run). */
  shared?: boolean;
  archived?: boolean;
}

export interface Catchment {
  id: string;
  input: CatchmentInput;
  coordinate: Coordinate | null;
  isochrone: GeoJsonGeometry | null;
  status: JobStatus;
  areas: CatchmentArea[];
  createdBy: string;
  createdAt: string;
  error?: string;
}
