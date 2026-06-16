"use client";

import type {
  AddressableSegments,
  CatchmentContext,
  ContextMetric,
  DataConfidence,
  PricingRationale,
} from "@/lib/types/battlecard";
import { fmtValue } from "@/lib/format";

// Data-driven sections beyond the reference card: pricing rationale, addressable
// segment sizes, catchment-relative context and explicit data confidence. All
// derived from the same ONS inputs.

const CONFIDENCE_STYLE: Record<string, string> = {
  high: "bg-priority-high/15 text-priority-high",
  medium: "bg-priority-mid/15 text-priority-mid",
  low: "bg-priority-low/15 text-priority-low",
};

export function BattlecardInsights({
  pricing,
  segments,
  context,
  confidence,
  contextMetrics,
  objectiveLabel,
  priceSet = true,
  highlightSegment,
}: {
  pricing?: PricingRationale;
  segments?: AddressableSegments;
  context?: CatchmentContext;
  confidence?: DataConfidence;
  contextMetrics?: ContextMetric[];
  objectiveLabel?: string | null;
  /** Whether the run set a target price. When false the pricing read is omitted
   * rather than judged against the engine default the user never entered. */
  priceSet?: boolean;
  /** The searched audience segment id, so its addressable pool is emphasised. */
  highlightSegment?: string;
}) {
  // The addressable pool that matches the searched audience, emphasised so the
  // card speaks to the use case rather than reading generic.
  const highlightKey =
    highlightSegment === "first_time_buyer"
      ? "ftb"
      : highlightSegment === "downsizer"
        ? "downsizer"
        : highlightSegment === "growing_family" ||
            highlightSegment === "second_stepper"
          ? "family"
          : null;
  // Older stored Battlecards predate these sections. Render what is present and
  // skip the rest rather than crashing the drawer on a partial payload.
  // Objective focus metrics first, so the data points that matter for the
  // chosen business focus lead.
  const metrics = contextMetrics
    ? [...contextMetrics].sort(
        (a, b) => Number(b.highlight ?? false) - Number(a.highlight ?? false),
      )
    : [];
  return (
    <div className="space-y-4">
      {metrics.length > 0 && (
        <section className="rounded-card border border-neutral-200 p-4">
          <div className="mb-3 flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">Local context</h3>
            {objectiveLabel && (
              <span className="rounded-full bg-light-accent/10 px-2 py-0.5 text-[11px] font-semibold text-light-accent">
                Focus: {objectiveLabel}
              </span>
            )}
          </div>
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {metrics.map((m) => (
              <div
                key={m.key}
                className={
                  m.highlight
                    ? "rounded-card bg-light-accent/5 p-2 ring-1 ring-light-accent/30"
                    : ""
                }
              >
                <dt className="text-xs text-neutral-500">{m.label}</dt>
                <dd
                  className={`text-sm font-semibold tabular-nums ${
                    m.highlight ? "text-light-accent" : ""
                  }`}
                >
                  {m.value}
                  <span className="ml-1 text-xs font-normal text-neutral-400">
                    {m.unit}
                  </span>
                </dd>
              </div>
            ))}
          </dl>
        </section>
      )}
      {pricing && (
        <section className="rounded-card border border-neutral-200 p-4">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold">Pricing rationale</h3>
            {confidence && (
              <span
                className={`rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase ${
                  CONFIDENCE_STYLE[confidence.level]
                }`}
              >
                {confidence.level} confidence
              </span>
            )}
          </div>
          {priceSet ? (
            <p className="output-prose text-sm leading-relaxed">
              {pricing.positioning}
            </p>
          ) : (
            <p className="text-sm leading-relaxed text-neutral-500">
              No target price was set for this run, so there is no pricing read
              for this site. Add a price band when you build to see the
              affordability and price story. Local incomes and sale prices are in
              the stats and charts.
            </p>
          )}
        </section>
      )}

      {segments && (
        <section className="rounded-card border border-neutral-200 p-4">
          <h3 className="mb-3 text-sm font-semibold">
            Addressable segments in catchment
          </h3>
          <dl className="grid grid-cols-3 gap-3">
            <Stat
              label="FTB pipeline"
              value={fmtValue(segments.firstTimeBuyerPipeline)}
              highlight={highlightKey === "ftb"}
            />
            <Stat
              label="Downsizer pool"
              value={fmtValue(segments.downsizerPool)}
              highlight={highlightKey === "downsizer"}
            />
            <Stat
              label="Family households"
              value={fmtValue(segments.familyHouseholds)}
              highlight={highlightKey === "family"}
            />
          </dl>
        </section>
      )}

      {context && context.incomeIndex.value !== null && (
        <section className="rounded-card border border-neutral-200 p-4">
          <h3 className="mb-3 text-sm font-semibold">Versus the catchment</h3>
          <dl className="grid grid-cols-2 gap-3">
            <Stat
              label="Income index (100 = avg)"
              value={fmtValue(context.incomeIndex)}
            />
            <Stat
              label="Share of catchment pop."
              value={
                context.shareOfCatchmentPopulation.value === null
                  ? "Not available"
                  : `${context.shareOfCatchmentPopulation.value}%`
              }
            />
          </dl>
        </section>
      )}

      {confidence && confidence.suppressedFields.length > 0 && (
        <p className="text-xs text-neutral-500">
          Suppressed inputs: {confidence.suppressedFields.join(", ")}.{" "}
          {confidence.note}
        </p>
      )}
    </div>
  );
}

function Stat({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-card border p-3 ${
        highlight
          ? "border-light-accent/40 bg-light-accent/5 ring-1 ring-light-accent/30"
          : "border-neutral-200"
      }`}
    >
      <dt className="text-xs text-neutral-500">{label}</dt>
      <dd
        className={`mt-0.5 text-sm font-semibold ${highlight ? "text-light-accent" : ""}`}
      >
        {value}
      </dd>
    </div>
  );
}
