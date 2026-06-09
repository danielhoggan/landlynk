"use client";

import { useEffect, useState } from "react";
import { Sparkles, RefreshCw } from "lucide-react";
import {
  generateAreaProfile,
  getUsage,
  type AreaProfile,
  type LlmUsage,
} from "@/lib/client";

const CATEGORY_ORDER = [
  "Transport",
  "Retail",
  "Leisure",
  "Education",
  "Healthcare",
  "Other",
];

// AI Local Area Profile for the catchment (or the starred selection). Generated
// on demand, cached server-side, and clearly labelled AI-generated for review.
export function AreaProfilePanel({
  catchmentId,
  starred,
}: {
  catchmentId: string;
  starred: string[];
}) {
  const [profile, setProfile] = useState<AreaProfile | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [usage, setUsage] = useState<LlmUsage | null>(null);
  const [costAck, setCostAck] = useState(false);
  const [pending, setPending] = useState<{
    scope: "whole" | "selection";
    refresh: boolean;
  } | null>(null);

  useEffect(() => {
    getUsage()
      .then(setUsage)
      .catch(() => setUsage({ metered: false }));
  }, []);

  const metered = usage?.metered === true;
  const exhausted =
    metered && usage?.remaining != null && usage.remaining <= 0;

  // Internal users see a one-time cost confirmation; external users draw on a
  // metered allowance, so the cost is already governed and no prompt is shown.
  function requestRun(scope: "whole" | "selection", refresh = false) {
    if (!metered && !costAck) {
      setPending({ scope, refresh });
      return;
    }
    run(scope, refresh);
  }

  async function run(scope: "whole" | "selection", refresh = false) {
    setBusy(true);
    setError("");
    setPending(null);
    try {
      const result = await generateAreaProfile(catchmentId, {
        scope,
        areaCodes: scope === "selection" ? starred : undefined,
        refresh,
      });
      setProfile(result);
      getUsage()
        .then(setUsage)
        .catch(() => {});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not generate profile");
    } finally {
      setBusy(false);
    }
  }

  const grouped = (profile?.amenities ?? []).reduce<Record<string, string[]>>(
    (acc, a) => {
      (acc[a.category] ??= []).push(a.name);
      return acc;
    },
    {},
  );

  return (
    <div className="rounded-card border border-neutral-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          <Sparkles size={16} className="text-light-accent" /> Local area profile
        </h2>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => requestRun("whole")}
            disabled={busy || exhausted}
            className="rounded-card bg-light-accent px-3 py-1.5 text-xs font-semibold text-white transition hover:brightness-95 disabled:opacity-50"
          >
            {busy ? "Generating..." : "Whole catchment"}
          </button>
          {starred.length > 0 && (
            <button
              type="button"
              onClick={() => requestRun("selection")}
              disabled={busy || exhausted}
              className="rounded-card border border-light-accent px-3 py-1.5 text-xs font-semibold text-light-accent transition hover:bg-light-accent/5 disabled:opacity-50"
            >
              Starred ({starred.length})
            </button>
          )}
          {profile && (
            <button
              type="button"
              onClick={() => requestRun("whole", true)}
              disabled={busy || exhausted}
              aria-label="Regenerate"
              title="Regenerate"
              className="rounded-card border border-neutral-300 p-1.5 text-neutral-500 hover:bg-neutral-100 disabled:opacity-50"
            >
              <RefreshCw size={14} />
            </button>
          )}
        </div>
      </div>

      {/* External users: metered allowance. */}
      {metered && (
        <p className="mt-2 text-xs text-neutral-500">
          {usage?.cap == null
            ? `${usage?.used ?? 0} generations used this month`
            : `${usage?.remaining ?? 0} of ${usage.cap} AI generations left this month`}
          {exhausted && (
            <span className="text-priority-low">
              {" "}
              — allowance reached, resets next month.
            </span>
          )}
        </p>
      )}

      {/* Internal users: one-time cost confirmation. */}
      {pending && (
        <div className="mt-2 rounded-card border border-priority-mid/40 bg-priority-mid/10 p-2.5 text-xs">
          <p className="text-neutral-700">
            This runs an AI model and incurs a cost to your account. Continue?
          </p>
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              onClick={() => {
                setCostAck(true);
                run(pending.scope, pending.refresh);
              }}
              className="rounded-card bg-light-accent px-3 py-1 font-semibold text-white"
            >
              Generate (incurs cost)
            </button>
            <button
              type="button"
              onClick={() => setPending(null)}
              className="rounded-card border border-neutral-300 px-3 py-1 font-semibold"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {error && <p className="mt-2 text-xs text-priority-low">{error}</p>}

      {!profile && !error && !pending && (
        <p className="mt-2 text-xs text-neutral-500">
          Generate an AI summary of the area and its amenities. Review before use.
        </p>
      )}

      {profile && (
        <div className="mt-3 space-y-3">
          <p className="output-prose text-sm leading-relaxed">
            {profile.description}
          </p>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {CATEGORY_ORDER.filter((c) => grouped[c]?.length).map((cat) => (
              <div
                key={cat}
                className="rounded-card border border-neutral-200 p-2"
              >
                <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-neutral-400">
                  {cat}
                </p>
                <ul className="space-y-0.5 text-xs text-neutral-700">
                  {grouped[cat].map((name) => (
                    <li key={name}>{name}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <p className="text-[11px] text-neutral-400">
            AI-generated{profile.model ? ` by ${profile.model}` : ""}
            {profile.cached ? " (cached)" : ""}. Please review before use. Included
            in the matching combined export.
          </p>
        </div>
      )}
    </div>
  );
}
