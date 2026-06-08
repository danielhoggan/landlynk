"use client";

import type {
  AddressableSegments,
  CatchmentContext,
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
}: {
  pricing: PricingRationale;
  segments: AddressableSegments;
  context: CatchmentContext;
  confidence: DataConfidence;
}) {
  return (
    <div className="space-y-4">
      <section className="rounded-card border border-neutral-200 p-4 dark:border-neutral-700">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-sm font-semibold">Pricing rationale</h3>
          <span
            className={`rounded-full px-2 py-0.5 text-[11px] font-semibold uppercase ${
              CONFIDENCE_STYLE[confidence.level]
            }`}
          >
            {confidence.level} confidence
          </span>
        </div>
        <p className="output-prose text-sm leading-relaxed">{pricing.positioning}</p>
      </section>

      <section className="rounded-card border border-neutral-200 p-4 dark:border-neutral-700">
        <h3 className="mb-3 text-sm font-semibold">Addressable segments in catchment</h3>
        <dl className="grid grid-cols-3 gap-3">
          <Stat label="FTB pipeline" value={fmtValue(segments.firstTimeBuyerPipeline)} />
          <Stat label="Downsizer pool" value={fmtValue(segments.downsizerPool)} />
          <Stat label="Family households" value={fmtValue(segments.familyHouseholds)} />
        </dl>
      </section>

      {context.incomeIndex.value !== null && (
        <section className="rounded-card border border-neutral-200 p-4 dark:border-neutral-700">
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

      {confidence.suppressedFields.length > 0 && (
        <p className="text-xs text-neutral-500">
          Suppressed inputs: {confidence.suppressedFields.join(", ")}. {confidence.note}
        </p>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-card border border-neutral-200 p-3 dark:border-neutral-700">
      <dt className="text-xs text-neutral-500">{label}</dt>
      <dd className="mt-0.5 text-sm font-semibold">{value}</dd>
    </div>
  );
}
