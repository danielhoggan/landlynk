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
export function areaMatchesFilter(
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
