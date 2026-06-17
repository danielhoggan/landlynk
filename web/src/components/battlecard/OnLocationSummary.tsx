"use client";

import type { Battlecard } from "@/lib/types/battlecard";
import { PRIORITY_COLORS, PRIORITY_LABELS } from "@/lib/priority";
import { fmtValue, fmtCurrency, fmtPercent } from "@/lib/format";

interface OnLocationSummaryProps {
  battlecard: Battlecard;
  /** The area's name (e.g. the MSOA name); leads the header. */
  areaName?: string;
  /** Catchment and national average household income, for comparison. */
  incomeBenchmark?: { national: number | null; catchment: number | null };
}

// The compact breakdown shown before the full deep-dive (design-framework.md,
// on-location summary). Leads with the area, then the key signals.
export function OnLocationSummary({
  battlecard,
  areaName,
  incomeBenchmark,
}: OnLocationSummaryProps) {
  const { visualSummary: vs, score, areaCode, rank } = battlecard;
  const stats = vs.keyStatistics;
  const ukIncome =
    incomeBenchmark?.national != null
      ? `UK ${shortMoney(incomeBenchmark.national)}${
          incomeBenchmark.catchment != null
            ? ` · area ${shortMoney(incomeBenchmark.catchment)}`
            : ""
        }`
      : undefined;

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">{areaName ?? areaCode}</h2>
          <p className="text-xs text-neutral-500">
            {areaCode}
            {vs.header.developmentName ? ` · ${vs.header.developmentName}` : ""}
          </p>
        </div>
        <span
          className="flex shrink-0 items-center gap-1.5 rounded-card px-2.5 py-1 text-xs font-semibold text-white"
          style={{ backgroundColor: PRIORITY_COLORS[score.band] }}
        >
          #{rank} {PRIORITY_LABELS[score.band]}
        </span>
      </div>

      <dl className="grid grid-cols-2 gap-3">
        <Stat label="Priority score" value={score.total.toFixed(2)} />
        <Stat
          label="Addressable population"
          value={fmtValue(stats.populationCatchment)}
        />
        <Stat
          label="Average household income"
          value={fmtCurrency(stats.averageHouseholdIncome)}
          sub={ukIncome}
        />
        <Stat
          label="Local house price"
          value={fmtCurrency(stats.medianHousePrice)}
        />
        <Stat
          label="Owner-occupied"
          value={fmtPercent(stats.ownerOccupiedPercentage)}
        />
        <Stat label="Median age" value={fmtValue(stats.medianAge)} />
        <Stat
          label="Income vs catchment"
          value={
            battlecard.catchmentContext.incomeIndex.value == null
              ? "n/a"
              : `${battlecard.catchmentContext.incomeIndex.value} (100=avg)`
          }
        />
      </dl>
    </div>
  );
}

function Stat({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div className="rounded-card border border-neutral-200 p-3">
      <dt className="text-xs text-neutral-500">{label}</dt>
      <dd className="mt-0.5 text-sm font-semibold">{value}</dd>
      {sub && <p className="mt-0.5 text-[10px] text-neutral-400">{sub}</p>}
    </div>
  );
}

function shortMoney(v: number): string {
  if (v >= 1_000_000) return `£${(v / 1_000_000).toFixed(1)}m`;
  if (v >= 1_000) return `£${Math.round(v / 1_000)}k`;
  return `£${Math.round(v)}`;
}
