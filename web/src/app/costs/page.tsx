"use client";

import { useCallback, useEffect, useState } from "react";
import { PoundSterling, Search } from "lucide-react";
import { getCosts, type CostReport, type CostRow } from "@/lib/client";
import { useUser } from "@/lib/userContext";

const gbp = (n: number) => `£${n.toFixed(3)}`;

// Admin-only AI cost report: total spend and breakdowns by user, model and
// brand group, with recent line items. Costs are indicative estimates from
// per-model pricing, for budgeting.
export default function CostsPage() {
  const { isAdmin, loading } = useUser();
  const [report, setReport] = useState<CostReport | null>(null);
  const [error, setError] = useState("");
  const [f, setF] = useState({ dateFrom: "", dateTo: "" });

  const load = useCallback(async () => {
    setError("");
    try {
      setReport(await getCosts(f));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    }
  }, [f]);

  useEffect(() => {
    if (isAdmin) load();
  }, [isAdmin, load]);

  if (loading) return <p className="p-4 text-sm text-neutral-500">Loading...</p>;
  if (!isAdmin) {
    return (
      <div className="mx-auto max-w-2xl p-4">
        <p className="rounded-card border border-neutral-200 bg-white p-4 text-sm text-neutral-600">
          This page is for admins only.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-4 p-4">
      <h1 className="flex items-center gap-2 text-lg font-semibold">
        <PoundSterling size={20} /> Costs
      </h1>
      <p className="text-sm text-neutral-500">
        AI generation spend. Figures are indicative estimates from per-model
        pricing, for budgeting not billing. Cached lookups are free and not
        counted.
      </p>

      <div className="flex flex-wrap items-end gap-2">
        <label className="flex items-center gap-1 text-xs text-neutral-500">
          From
          <input
            type="date"
            value={f.dateFrom}
            onChange={(e) => setF((p) => ({ ...p, dateFrom: e.target.value }))}
            className="rounded-card border border-neutral-300 px-2 py-1 text-xs"
          />
        </label>
        <label className="flex items-center gap-1 text-xs text-neutral-500">
          To
          <input
            type="date"
            value={f.dateTo}
            onChange={(e) => setF((p) => ({ ...p, dateTo: e.target.value }))}
            className="rounded-card border border-neutral-300 px-2 py-1 text-xs"
          />
        </label>
        <button
          type="button"
          onClick={load}
          className="flex items-center gap-1.5 rounded-card bg-light-accent px-3 py-1.5 text-xs font-semibold text-white"
        >
          <Search size={14} /> Apply
        </button>
      </div>

      {error && <p className="text-sm text-priority-low">{error}</p>}

      {report && (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-card border border-neutral-200 bg-white p-4">
              <p className="text-xs text-neutral-500">Total cost</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums">
                {gbp(report.total)}
              </p>
            </div>
            <div className="rounded-card border border-neutral-200 bg-white p-4">
              <p className="text-xs text-neutral-500">Tokens</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums">
                {report.tokens.toLocaleString()}
              </p>
            </div>
            <div className="rounded-card border border-neutral-200 bg-white p-4">
              <p className="text-xs text-neutral-500">Generations</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums">
                {report.generations}
              </p>
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <Breakdown title="By user" rows={report.byUser} labelKey="actorEmail" />
            <Breakdown title="By model" rows={report.byModel} labelKey="model" />
            <Breakdown title="By brand" rows={report.byGroup} labelKey="groupName" />
          </div>

          <div className="overflow-x-auto rounded-card border border-neutral-200 bg-white">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-neutral-200 text-neutral-500">
                <tr>
                  <th className="px-3 py-2 font-semibold">When</th>
                  <th className="px-3 py-2 font-semibold">User</th>
                  <th className="px-3 py-2 font-semibold">Brand</th>
                  <th className="px-3 py-2 font-semibold">Model</th>
                  <th className="px-3 py-2 font-semibold">Job</th>
                  <th className="px-3 py-2 text-right font-semibold">Tokens</th>
                  <th className="px-3 py-2 text-right font-semibold">Cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {report.items.map((it, i) => (
                  <tr key={i}>
                    <td className="whitespace-nowrap px-3 py-2 text-neutral-500">
                      {it.createdAt
                        ? new Date(it.createdAt).toLocaleString()
                        : "-"}
                    </td>
                    <td className="px-3 py-2">{it.actorEmail ?? "system"}</td>
                    <td className="px-3 py-2 text-neutral-500">
                      {it.groupName ?? ""}
                    </td>
                    <td className="px-3 py-2">{it.model ?? ""}</td>
                    <td className="px-3 py-2 font-mono text-[11px] text-neutral-400">
                      {it.catchmentId?.slice(0, 8) ?? ""}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-neutral-500">
                      {(it.tokens ?? 0).toLocaleString()}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {gbp(it.cost)}
                    </td>
                  </tr>
                ))}
                {report.items.length === 0 && (
                  <tr>
                    <td
                      colSpan={7}
                      className="px-3 py-6 text-center text-neutral-400"
                    >
                      No AI spend in this range.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function Breakdown({
  title,
  rows,
  labelKey,
}: {
  title: string;
  rows: CostRow[];
  labelKey: keyof CostRow;
}) {
  return (
    <div className="rounded-card border border-neutral-200 bg-white p-4">
      <h2 className="mb-2 text-sm font-semibold">{title}</h2>
      <ul className="space-y-1 text-xs">
        {rows.map((r, i) => (
          <li key={i} className="flex items-center justify-between gap-2">
            <span className="truncate text-neutral-600">
              {String(r[labelKey] ?? "unknown")}
            </span>
            <span className="tabular-nums text-neutral-500">
              {r.generations} · £{Number(r.cost).toFixed(3)}
            </span>
          </li>
        ))}
        {rows.length === 0 && <li className="text-neutral-400">None</li>}
      </ul>
    </div>
  );
}
