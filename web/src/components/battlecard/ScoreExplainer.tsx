"use client";

import type { ScoreBreakdown } from "@/lib/types/battlecard";

const SIGNAL_LABELS: Record<string, string> = {
  incomeFit: "Income fit",
  tenureSignal: "Tenure signal",
  ageSkew: "Age skew",
  addressableScale: "Addressable scale",
  householdType: "Household type",
  incomeLevel: "Income level",
  lowDeprivation: "Low deprivation",
  greenSpace: "Green space",
  schools: "Schools",
  lowCrime: "Low crime",
  healthcareAccess: "Healthcare access",
};

// Every area's deep-dive shows why it scored as it did (SCOPING.md Section 8).
// This renders the weighted signal contributions so the ranking is explainable.
export function ScoreExplainer({ score }: { score: ScoreBreakdown }) {
  return (
    <section className="rounded-card border border-neutral-200 p-4">
      <h3 className="mb-3 text-sm font-semibold">
        Why this area scored {score.total.toFixed(2)}
      </h3>
      <ul className="space-y-2">
        {score.contributions.map((c) => (
          <li key={c.signal}>
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium">
                {SIGNAL_LABELS[c.signal] ?? c.signal}
              </span>
              <span className="text-neutral-500">
                {c.contribution.toFixed(2)} ({(c.weight * 100).toFixed(0)}%
                weight)
              </span>
            </div>
            <div className="mt-1 h-1.5 w-full rounded-full bg-neutral-200">
              <div
                className="h-1.5 rounded-full bg-light-accent"
                style={{ width: `${Math.round(c.rawScore * 100)}%` }}
              />
            </div>
            <p className="mt-1 text-xs text-neutral-500">{c.rationale}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
