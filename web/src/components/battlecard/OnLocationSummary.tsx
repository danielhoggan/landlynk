"use client";

import type { Battlecard } from "@/lib/types/battlecard";
import { PRIORITY_COLORS, PRIORITY_LABELS } from "@/lib/priority";
import { fmtValue, fmtCurrency, fmtPercent } from "@/lib/format";

interface OnLocationSummaryProps {
  battlecard: Battlecard;
  onOpenFull: () => void;
}

// The compact breakdown shown before the full deep-dive (design-framework.md,
// on-location summary). Area name and code, priority rank and score,
// addressable population, and the key signals as short labelled values.
export function OnLocationSummary({
  battlecard,
  onOpenFull,
}: OnLocationSummaryProps) {
  const { visualSummary: vs, score, areaCode, rank } = battlecard;
  const stats = vs.keyStatistics;

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold">{vs.header.developmentName}</h2>
          <p className="text-xs text-neutral-500">
            {areaCode} - {vs.header.town}
          </p>
        </div>
        <span
          className="flex items-center gap-1.5 rounded-card px-2.5 py-1 text-xs font-semibold text-white"
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
        />
        <Stat
          label="Owner-occupied"
          value={fmtPercent(stats.ownerOccupiedPercentage)}
        />
        <Stat label="Median age" value={fmtValue(stats.medianAge)} />
        <Stat label="Bed range" value={stats.bedRange} />
      </dl>

      <button
        type="button"
        onClick={onOpenFull}
        className="w-full rounded-card bg-light-accent py-2.5 text-sm font-semibold text-white dark:bg-dark-accent"
      >
        Open full Battlecard
      </button>
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
