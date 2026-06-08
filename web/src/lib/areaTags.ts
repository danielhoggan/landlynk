import type { AreaMetrics, CatchmentArea } from "./types/catchment";

// Strategic signal tags derived from an area's metrics, used for filtering the
// results and labelling areas. Thresholds are deliberately simple and
// explainable; tune here if the business definition changes.

export interface SignalTag {
  id: string;
  label: string;
  /** True if the area's metrics qualify for this tag. */
  match: (m: AreaMetrics) => boolean;
}

export const SIGNAL_TAGS: SignalTag[] = [
  {
    id: "ftb",
    label: "First-time buyer",
    // A high private-rented share is the buyer pipeline.
    match: (m) => (m.privateRented ?? 0) >= 25,
  },
  {
    id: "downsizer",
    label: "Downsizer",
    // Outright ownership points to equity-rich movers.
    match: (m) => (m.ownsOutright ?? 0) >= 30,
  },
  {
    id: "high_net_worth",
    label: "High net worth",
    // Income well above the catchment average.
    match: (m) => (m.incomeIndex ?? 0) >= 120,
  },
  {
    id: "family",
    label: "Family",
    match: (m) => (m.familyShare ?? 0) >= 60,
  },
];

/** The tags an area qualifies for. */
export function tagsForArea(area: CatchmentArea): SignalTag[] {
  if (!area.metrics) return [];
  return SIGNAL_TAGS.filter((t) => t.match(area.metrics as AreaMetrics));
}

/** Whether an area matches the selected tag filter (any of the selected tags). */
export function areaMatchesTags(
  area: CatchmentArea,
  selected: Set<string>,
): boolean {
  if (selected.size === 0) return true;
  const ids = new Set(tagsForArea(area).map((t) => t.id));
  for (const id of selected) {
    if (ids.has(id)) return true;
  }
  return false;
}

// Numeric metrics the results can be range-filtered on.
export type MetricKey =
  | "income"
  | "housePrice"
  | "medianAge"
  | "ownerOccupied"
  | "privateRented"
  | "familyShare";

export interface MetricFilterDef {
  key: MetricKey;
  label: string;
  prefix?: string;
  suffix?: string;
}

export const METRIC_FILTERS: MetricFilterDef[] = [
  { key: "income", label: "Avg income", prefix: "£" },
  { key: "housePrice", label: "House price", prefix: "£" },
  { key: "medianAge", label: "Median age" },
  { key: "ownerOccupied", label: "Owner-occupied", suffix: "%" },
  { key: "privateRented", label: "Private rented", suffix: "%" },
  { key: "familyShare", label: "Family households", suffix: "%" },
];

export type MetricRanges = Partial<
  Record<MetricKey, { min?: number; max?: number }>
>;

/** Whether an area passes both the tag filter and all active numeric ranges. */
export function areaMatchesFilters(
  area: CatchmentArea,
  tags: Set<string>,
  ranges: MetricRanges,
): boolean {
  if (!areaMatchesTags(area, tags)) return false;
  for (const [key, range] of Object.entries(ranges)) {
    if (!range || (range.min == null && range.max == null)) continue;
    const val = area.metrics ? area.metrics[key as MetricKey] : null;
    if (val == null) return false;
    if (range.min != null && val < range.min) return false;
    if (range.max != null && val > range.max) return false;
  }
  return true;
}
