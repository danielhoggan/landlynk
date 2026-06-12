import type { AreaMetrics, CatchmentArea } from "./types/catchment";

// Strategic signal tags derived from an area's metrics, used for filtering the
// results and labelling areas. Thresholds are deliberately simple and
// explainable; tune here if the business definition changes.

// Some signals are best judged relative to the catchment, not an absolute bar:
// "family" share varies hugely between, say, a student city and a commuter belt,
// so a fixed threshold either matches everything or (as reported) nothing. The
// context carries catchment-derived reference points for those tags.
export interface TagContext {
  /** Family-household share at or above which an area counts as family-skewed. */
  familyShareThreshold: number;
  /**
   * Household income at or above which an area counts as high net worth. Derived
   * from the catchment (top third) so the tag adapts to the local norm; null
   * when no income is available, falling back to the absolute income index.
   */
  highIncomeThreshold: number | null;
}

const DEFAULT_CONTEXT: TagContext = {
  familyShareThreshold: 55,
  highIncomeThreshold: null,
};

function percentile(values: number[], fraction: number): number {
  return values[Math.min(values.length - 1, Math.floor(values.length * fraction))];
}

/** Reference points for relative tags, derived from the whole catchment. */
export function buildTagContext(areas: CatchmentArea[]): TagContext {
  const shares = areas
    .map((a) => a.metrics?.familyShare)
    .filter((v): v is number => v != null)
    .sort((a, b) => a - b);
  const incomes = areas
    .map((a) => a.metrics?.income)
    .filter((v): v is number => v != null)
    .sort((a, b) => a - b);
  return {
    // The catchment median: "family areas" are the upper half, so the filter
    // always returns a sensible subset and adapts to the local norm.
    familyShareThreshold: shares.length
      ? shares[Math.floor(shares.length / 2)]
      : DEFAULT_CONTEXT.familyShareThreshold,
    // Top third by income marks the high-net-worth areas, relative to the
    // catchment. An absolute income-index bar matched nothing in tighter,
    // uniformly-priced catchments.
    highIncomeThreshold: incomes.length ? percentile(incomes, 2 / 3) : null,
  };
}

export interface SignalTag {
  id: string;
  label: string;
  /** True if the area's metrics qualify for this tag, given the catchment. */
  match: (m: AreaMetrics, ctx: TagContext) => boolean;
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
    // The wealthiest areas relative to the catchment (top third by income);
    // falls back to the absolute income index when income is unavailable.
    match: (m, ctx) =>
      ctx.highIncomeThreshold != null && m.income != null
        ? m.income >= ctx.highIncomeThreshold
        : (m.incomeIndex ?? 0) >= 120,
  },
  {
    id: "family",
    label: "Family",
    // Relative to the catchment: family-skewed areas (upper half by family
    // household share), so the filter never empties and suits the local mix.
    match: (m, ctx) =>
      m.familyShare != null && m.familyShare >= ctx.familyShareThreshold,
  },
];

/** The tags an area qualifies for, given the catchment context. */
export function tagsForArea(
  area: CatchmentArea,
  ctx: TagContext = DEFAULT_CONTEXT,
): SignalTag[] {
  if (!area.metrics) return [];
  return SIGNAL_TAGS.filter((t) => t.match(area.metrics as AreaMetrics, ctx));
}

/** Whether an area matches the selected tag filter (any of the selected tags). */
export function areaMatchesTags(
  area: CatchmentArea,
  selected: Set<string>,
  ctx: TagContext = DEFAULT_CONTEXT,
): boolean {
  if (selected.size === 0) return true;
  const ids = new Set(tagsForArea(area, ctx).map((t) => t.id));
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
  ctx?: TagContext,
): boolean {
  if (!areaMatchesTags(area, tags, ctx)) return false;
  for (const [key, range] of Object.entries(ranges)) {
    if (!range || (range.min == null && range.max == null)) continue;
    const val = area.metrics ? area.metrics[key as MetricKey] : null;
    if (val == null) return false;
    if (range.min != null && val < range.min) return false;
    if (range.max != null && val > range.max) return false;
  }
  return true;
}
