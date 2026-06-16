"use client";

import { useEffect, useState } from "react";
import { Gauge, Layers } from "lucide-react";
import { getCatchmentVerdict, type CatchmentVerdict } from "@/lib/client";

function money(v: number | null | undefined): string {
  if (v == null) return "n/a";
  if (v >= 1_000_000) return `£${(v / 1_000_000).toFixed(1)}m`;
  if (v >= 1_000) return `£${Math.round(v / 1_000)}k`;
  return `£${Math.round(v).toLocaleString()}`;
}

function count(v: number | null | undefined): string {
  return v == null ? "n/a" : Math.round(v).toLocaleString();
}

const PRICE_FIT: Record<
  CatchmentVerdict["priceFit"],
  { label: string; cls: string }
> = {
  within: { label: "Within local reach", cls: "bg-priority-high text-white" },
  stretch: { label: "A modest stretch", cls: "bg-priority-mid text-white" },
  above: { label: "Above local means", cls: "bg-priority-low text-white" },
  unknown: { label: "Income data incomplete", cls: "bg-neutral-300 text-neutral-700" },
};

// The three addressable pools we size, with their audience label and a product
// hint for the next-phase recommendation.
const SEGMENTS: {
  key: keyof CatchmentVerdict["segments"];
  label: string;
  product: string;
}[] = [
  { key: "firstTimeBuyer", label: "First-time buyers", product: "2 to 3 bed homes and apartments" },
  { key: "downsizer", label: "Downsizers", product: "2 to 3 bed bungalows and low-maintenance homes" },
  { key: "family", label: "Families", product: "3 to 4 bed family homes" },
];

function useVerdict(catchmentId: string) {
  const [verdict, setVerdict] = useState<CatchmentVerdict | null>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    setLoading(true);
    getCatchmentVerdict(catchmentId)
      .then((v) => active && setVerdict(v))
      .catch(() => {})
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [catchmentId]);
  return { verdict, loading };
}

// Intent 2: a headline appraisal verdict for a site under consideration.
export function VerdictPanel({ catchmentId }: { catchmentId: string }) {
  const { verdict, loading } = useVerdict(catchmentId);
  if (loading || !verdict) return null;
  const fit = PRICE_FIT[verdict.priceFit];

  return (
    <div className="space-y-3 rounded-card border border-neutral-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          <Gauge size={16} className="text-light-accent" /> Site verdict
        </h2>
        {verdict.priceSet && (
          <span
            className={`rounded-full px-3 py-1 text-xs font-semibold ${fit.cls}`}
          >
            Price fit: {fit.label}
          </span>
        )}
      </div>
      {verdict.priceSet ? (
        <p className="text-sm text-neutral-600">{verdict.positioning}</p>
      ) : (
        <p className="rounded-card border border-priority-mid/40 bg-priority-mid/10 p-3 text-sm text-neutral-600">
          No target price was set for this run, so there is no price-fit yet. Add
          a price band in the brief to see how it sits against local incomes and
          sale prices. The local figures below are from the area data.
        </p>
      )}
      <div className="grid gap-2 sm:grid-cols-3">
        <Stat
          label="Price from"
          value={verdict.priceSet ? money(verdict.priceFrom) : "Not set"}
        />
        <Stat
          label="Locally affordable"
          value={money(verdict.impliedAffordablePrice)}
        />
        <Stat label="Local sale price" value={money(verdict.medianHousePrice)} />
      </div>
      <p className="text-[11px] font-semibold uppercase tracking-wider text-neutral-400">
        Addressable demand
      </p>
      <div className="grid gap-2 sm:grid-cols-3">
        {SEGMENTS.map((s) => (
          <Stat
            key={s.key}
            label={`${s.label} (households)`}
            value={count(verdict.segments[s.key])}
          />
        ))}
      </div>
      <p className="text-[11px] text-neutral-400">
        Data confidence: {verdict.confidence}. Across the whole catchment.
      </p>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-card border border-neutral-200 px-3 py-2">
      <p className="text-lg font-semibold text-light-accent">{value}</p>
      <p className="text-[11px] text-neutral-500">{label}</p>
    </div>
  );
}

// Intent 3: recommend the product mix for the final phase. The user marks the
// audiences that are selling slowly; we recommend the deepest pool that is left.
export function MixPanel({ catchmentId }: { catchmentId: string }) {
  const { verdict, loading } = useVerdict(catchmentId);
  const [slow, setSlow] = useState<Set<string>>(new Set());
  if (loading || !verdict) return null;

  const toggle = (key: string) =>
    setSlow((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });

  const ranked = SEGMENTS.map((s) => ({
    ...s,
    pool: verdict.segments[s.key] ?? 0,
  })).sort((a, b) => b.pool - a.pool);
  const recommended = ranked.find((s) => !slow.has(s.key) && s.pool > 0);

  return (
    <div className="space-y-3 rounded-card border border-neutral-200 bg-white p-4">
      <h2 className="flex items-center gap-2 text-sm font-semibold">
        <Layers size={16} className="text-light-accent" /> Next-phase product mix
      </h2>
      <div>
        <p className="mb-1.5 text-xs font-medium text-neutral-500">
          Mark what is already selling slowly, so we steer away from it:
        </p>
        <div className="flex flex-wrap gap-2">
          {ranked.map((s) => (
            <button
              key={s.key}
              type="button"
              onClick={() => toggle(s.key)}
              className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                slow.has(s.key)
                  ? "bg-priority-low text-white"
                  : "border border-neutral-300 text-neutral-600 hover:bg-neutral-100"
              }`}
            >
              {s.label} · {count(s.pool)}
            </button>
          ))}
        </div>
      </div>
      {recommended ? (
        <div className="rounded-card border border-priority-high/40 bg-priority-high/10 p-3 text-sm">
          <p className="font-semibold">
            Recommended: build for {recommended.label.toLowerCase()}
          </p>
          <p className="mt-1 text-neutral-600">
            {recommended.label} are the deepest under-served pool in the catchment
            at {count(recommended.pool)} households. Lean the final phase toward{" "}
            {recommended.product}.
          </p>
        </div>
      ) : (
        <p className="rounded-card border border-priority-mid/40 bg-priority-mid/10 p-3 text-sm text-neutral-600">
          No addressable pool is left once those are excluded, or the household
          data is incomplete. Widen the catchment or load census data to size the
          remaining demand.
        </p>
      )}
      <p className="text-[11px] text-neutral-400">
        Demand is sized from the catchment census. Your own sales velocity by
        house type is not yet included.
      </p>
    </div>
  );
}
