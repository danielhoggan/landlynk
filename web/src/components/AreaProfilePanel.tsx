"use client";

import { useState } from "react";
import { Sparkles, RefreshCw } from "lucide-react";
import { generateAreaProfile, type AreaProfile } from "@/lib/client";

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

  async function run(scope: "whole" | "selection", refresh = false) {
    setBusy(true);
    setError("");
    try {
      const result = await generateAreaProfile(catchmentId, {
        scope,
        areaCodes: scope === "selection" ? starred : undefined,
        refresh,
      });
      setProfile(result);
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
            onClick={() => run("whole")}
            disabled={busy}
            className="rounded-card bg-light-accent px-3 py-1.5 text-xs font-semibold text-white transition hover:brightness-95 disabled:opacity-50"
          >
            {busy ? "Generating..." : "Whole catchment"}
          </button>
          {starred.length > 0 && (
            <button
              type="button"
              onClick={() => run("selection")}
              disabled={busy}
              className="rounded-card border border-light-accent px-3 py-1.5 text-xs font-semibold text-light-accent transition hover:bg-light-accent/5 disabled:opacity-50"
            >
              Starred ({starred.length})
            </button>
          )}
          {profile && (
            <button
              type="button"
              onClick={() => run("whole", true)}
              disabled={busy}
              aria-label="Regenerate"
              title="Regenerate"
              className="rounded-card border border-neutral-300 p-1.5 text-neutral-500 hover:bg-neutral-100 disabled:opacity-50"
            >
              <RefreshCw size={14} />
            </button>
          )}
        </div>
      </div>

      {error && <p className="mt-2 text-xs text-priority-low">{error}</p>}

      {!profile && !error && (
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
