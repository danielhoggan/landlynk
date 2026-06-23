"use client";

import { useEffect, useState } from "react";
import { Megaphone, RefreshCw } from "lucide-react";
import {
  generateMarketingPlaybook,
  getMarketingPlaybook,
  getUsage,
  type MarketingPlaybook,
  type LlmUsage,
} from "@/lib/client";

// Marketing Activation playbook for the whole catchment. A separate, optional
// pipeline for internal staff only: it spends an LLM call, so the cost is
// flagged and the run is opt-in. Generated server-side, cached, clearly labelled
// AI-generated for review. Never feeds the scoring.
export function MarketingActivationPanel({
  catchmentId,
  intent,
}: {
  catchmentId: string;
  /** The housebuilder intent of the run, passed so the plan is framed for it. */
  intent?: string | null;
}) {
  const [playbook, setPlaybook] = useState<MarketingPlaybook | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [usage, setUsage] = useState<LlmUsage | null>(null);
  const [pending, setPending] = useState<{ refresh: boolean } | null>(null);

  useEffect(() => {
    getUsage()
      .then(setUsage)
      .catch(() => setUsage({ metered: false }));
  }, []);

  // Auto-show a previously generated plan without spending a call, so reopening
  // a run shows its cached playbook.
  useEffect(() => {
    let active = true;
    getMarketingPlaybook(catchmentId)
      .then((p) => {
        if (active && p) setPlaybook(p);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [catchmentId]);

  async function run(refresh: boolean) {
    setBusy(true);
    setError("");
    setPending(null);
    try {
      const result = await generateMarketingPlaybook(catchmentId, {
        intent: intent ?? null,
        refresh,
      });
      setPlaybook(result);
      getUsage()
        .then(setUsage)
        .catch(() => {});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not generate playbook");
    } finally {
      setBusy(false);
    }
  }

  // The plan is a separate AI run, so flag the cost before spending it. Internal
  // staff are unmetered, so the note is framed around the LLM call and its
  // indicative cost rather than a monthly allowance.
  const refresh = pending?.refresh ?? false;
  const costLine =
    usage?.estCost != null && usage.estCost > 0
      ? `about £${usage.estCost.toFixed(2)}`
      : "an LLM call";
  const confirmText = `This ${
    refresh ? "regenerates the marketing plan" : "runs the marketing activation plan"
  }${usage?.model ? ` with ${usage.model}` : ""}, which costs ${costLine}. ` +
    "Already-generated plans are free.";

  return (
    <div className="rounded-card border border-neutral-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          <Megaphone size={16} className="text-light-accent" /> Marketing
          activation
          <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-neutral-500">
            Internal
          </span>
        </h2>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => (playbook ? run(false) : setPending({ refresh: false }))}
            disabled={busy}
            className="rounded-card bg-light-accent px-3 py-1.5 text-xs font-semibold text-white transition hover:brightness-95 disabled:opacity-50"
          >
            {busy ? "Generating..." : playbook ? "View plan" : "Generate plan"}
          </button>
          {playbook && (
            <button
              type="button"
              onClick={() => setPending({ refresh: true })}
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

      {pending && (
        <div className="mt-2 rounded-card border border-priority-mid/40 bg-priority-mid/10 p-2.5 text-xs">
          <p className="text-neutral-700">{confirmText} Run it?</p>
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              onClick={() => run(pending.refresh)}
              className="rounded-card bg-light-accent px-3 py-1 font-semibold text-white"
            >
              {refresh ? "Regenerate" : "Run plan"}
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

      {!playbook && !error && !pending && (
        <p className="mt-2 text-xs text-neutral-500">
          Turn this catchment into a launch media plan: budget split by audience
          tier, channel mix, Google Search themes, Meta audiences, watch-outs and
          KPIs. This is an optional AI run and costs an LLM call. Internal only.
        </p>
      )}

      {playbook && (
        <div className="mt-3 space-y-4">
          {playbook.summary && (
            <p className="output-prose text-sm leading-relaxed">
              {playbook.summary}
            </p>
          )}

          {playbook.budgetTiers.length > 0 && (
            <Block title="Budget split">
              <div className="space-y-1.5">
                {playbook.budgetTiers.map((t, i) => (
                  <div key={i} className="rounded-card border border-neutral-200 p-2.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-semibold">{t.tier}</span>
                      {t.sharePct != null && (
                        <span className="text-sm font-semibold tabular-nums text-light-accent">
                          {t.sharePct}%
                        </span>
                      )}
                    </div>
                    {t.audience && (
                      <p className="text-xs text-neutral-500">{t.audience}</p>
                    )}
                    {t.rationale && (
                      <p className="mt-1 text-xs text-neutral-600">{t.rationale}</p>
                    )}
                  </div>
                ))}
              </div>
            </Block>
          )}

          {playbook.channelMix.length > 0 && (
            <Block title="Channel mix">
              <div className="space-y-2">
                {playbook.channelMix.map((m, i) => (
                  <div key={i} className="rounded-card border border-neutral-200 p-2.5">
                    <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-neutral-400">
                      {m.tier}
                    </p>
                    <ul className="space-y-1 text-xs text-neutral-700">
                      {m.channels.map((c, j) => (
                        <li key={j} className="flex items-start justify-between gap-2">
                          <span className="min-w-0">
                            <span className="font-medium">{c.channel}</span>
                            {c.role ? (
                              <span className="text-neutral-500"> — {c.role}</span>
                            ) : null}
                          </span>
                          {c.sharePct != null && (
                            <span className="shrink-0 font-semibold tabular-nums text-light-accent">
                              {c.sharePct}%
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </Block>
          )}

          {playbook.searchThemes.length > 0 && (
            <Block title="Google Search themes">
              <div className="space-y-1.5">
                {playbook.searchThemes.map((s, i) => (
                  <div key={i} className="rounded-card border border-neutral-200 p-2.5">
                    <p className="text-sm font-semibold">{s.theme}</p>
                    {s.intent && (
                      <p className="text-xs text-neutral-500">{s.intent}</p>
                    )}
                    {s.exampleKeywords.length > 0 && (
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {s.exampleKeywords.map((k, j) => (
                          <span
                            key={j}
                            className="rounded-full bg-neutral-100 px-2 py-0.5 text-[11px] text-neutral-600"
                          >
                            {k}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </Block>
          )}

          {playbook.metaAudiences.length > 0 && (
            <Block title="Meta audiences">
              <div className="space-y-1.5">
                {playbook.metaAudiences.map((a, i) => (
                  <div key={i} className="rounded-card border border-neutral-200 p-2.5">
                    <p className="text-sm font-semibold">{a.name}</p>
                    {a.definition && (
                      <p className="text-xs text-neutral-600">{a.definition}</p>
                    )}
                    {a.creativeAngle && (
                      <p className="mt-1 text-xs italic text-neutral-500">
                        {a.creativeAngle}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </Block>
          )}

          {playbook.kpis.length > 0 && (
            <Block title="KPIs">
              <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {playbook.kpis.map((k, i) => (
                  <div key={i} className="rounded-card border border-neutral-200 p-2.5">
                    <dt className="text-xs text-neutral-500">{k.metric}</dt>
                    <dd className="text-sm font-semibold">{k.target}</dd>
                    {k.why && (
                      <p className="mt-0.5 text-[11px] text-neutral-400">{k.why}</p>
                    )}
                  </div>
                ))}
              </dl>
            </Block>
          )}

          {playbook.watchOuts.length > 0 && (
            <Block title="Watch-outs">
              <ul className="list-inside list-disc space-y-1 text-xs text-neutral-700">
                {playbook.watchOuts.map((w, i) => (
                  <li key={i}>{w}</li>
                ))}
              </ul>
            </Block>
          )}

          <p className="text-[11px] text-neutral-400">
            AI-generated{playbook.model ? ` by ${playbook.model}` : ""}
            {playbook.cached ? " (cached)" : ""}. A starting point for the media
            plan. Please review before use.
          </p>
        </div>
      )}
    </div>
  );
}

function Block({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-neutral-400">
        {title}
      </h3>
      {children}
    </div>
  );
}
