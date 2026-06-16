"use client";

import { Info } from "lucide-react";
import type { StoredConfig } from "@/lib/types/catchment";
import { loadSettings } from "@/lib/settings";

// Key card flagging when a saved run was built on assumptions that differ from
// the current defaults. The values stored with the run are the source of truth;
// this surfaces them so a reader is not misled by today's settings.

interface Diff {
  label: string;
  used: string;
  now: string;
}

const approxEqual = (a: number, b: number) => Math.abs(a - b) < 1e-9;

export function RunAssumptions({ config }: { config?: StoredConfig | null }) {
  if (!config) return null;
  const now = loadSettings();
  const diffs: Diff[] = [];

  if (
    config.affordabilityMultiple != null &&
    !approxEqual(config.affordabilityMultiple, now.affordabilityMultiple)
  ) {
    diffs.push({
      label: "Affordability multiple",
      used: `${config.affordabilityMultiple}×`,
      now: `${now.affordabilityMultiple}×`,
    });
  }
  if (
    config.overlapThreshold != null &&
    !approxEqual(config.overlapThreshold, now.overlapThreshold)
  ) {
    diffs.push({
      label: "Overlap threshold",
      used: String(config.overlapThreshold),
      now: String(now.overlapThreshold),
    });
  }
  // When the run used an objective, its weights are that objective's preset by
  // design, not a deviation from the user's defaults, so comparing them is
  // misleading. Only flag weight differences for runs scored on manual weights.
  if (!config.objective) {
    for (const [key, label] of Object.entries(WEIGHT_LABELS)) {
      const used = config.weights?.[key];
      const cur = now.weights[key as keyof typeof now.weights];
      if (used != null && cur != null && !approxEqual(used, cur)) {
        diffs.push({ label, used: String(used), now: String(cur) });
      }
    }
  }

  if (diffs.length === 0) return null;

  return (
    <div className="rounded-card border border-priority-mid/40 bg-priority-mid/10 p-4">
      <div className="flex items-center gap-2">
        <Info size={16} className="text-priority-mid" />
        <h2 className="text-sm font-semibold">
          This run used different assumptions
        </h2>
      </div>
      <p className="mt-1 text-xs text-neutral-600">
        The ranking and pricing below were built with the values stored at run
        time, which differ from your current defaults. The stored values are
        authoritative for this run.
      </p>
      <dl className="mt-3 grid gap-2 sm:grid-cols-2">
        {diffs.map((d) => (
          <div
            key={d.label}
            className="flex items-center justify-between rounded-card bg-white px-3 py-2 text-xs"
          >
            <dt className="text-neutral-500">{d.label}</dt>
            <dd className="font-semibold tabular-nums">
              {d.used}
              <span className="ml-2 font-normal text-neutral-400">
                now {d.now}
              </span>
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

const WEIGHT_LABELS: Record<string, string> = {
  income_fit: "Weight: income fit",
  tenure_signal: "Weight: tenure signal",
  age_skew: "Weight: age skew",
  addressable_scale: "Weight: addressable scale",
  household_type: "Weight: household type",
};
