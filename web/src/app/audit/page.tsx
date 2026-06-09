"use client";

import { useCallback, useEffect, useState } from "react";
import { ScrollText, Search } from "lucide-react";
import { getAudit, type AuditEntry } from "@/lib/client";
import { useUser } from "@/lib/userContext";

// Admin-only audit trail: who did what, when, to what, and any cost. Filterable
// by date, user, action and cost.
export default function AuditPage() {
  const { isAdmin, loading } = useUser();
  const [rows, setRows] = useState<AuditEntry[]>([]);
  const [error, setError] = useState("");
  const [f, setF] = useState({
    actor: "",
    action: "",
    minCost: "",
    dateFrom: "",
    dateTo: "",
  });
  const set = (k: keyof typeof f, v: string) =>
    setF((prev) => ({ ...prev, [k]: v }));

  const load = useCallback(async () => {
    setError("");
    try {
      setRows(await getAudit(f));
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
        <ScrollText size={20} /> Audits
      </h1>
      <p className="text-sm text-neutral-500">
        Every meaningful action: who, when, what, and any cost incurred.
      </p>

      <div className="grid gap-2 sm:grid-cols-6">
        <input
          value={f.actor}
          onChange={(e) => set("actor", e.target.value)}
          placeholder="User email"
          className="rounded-card border border-neutral-300 px-2 py-1.5 text-xs sm:col-span-2"
        />
        <input
          value={f.action}
          onChange={(e) => set("action", e.target.value)}
          placeholder="Action (e.g. ai.generate)"
          className="rounded-card border border-neutral-300 px-2 py-1.5 text-xs sm:col-span-2"
        />
        <input
          value={f.minCost}
          onChange={(e) => set("minCost", e.target.value)}
          placeholder="Min cost"
          type="number"
          className="rounded-card border border-neutral-300 px-2 py-1.5 text-xs"
        />
        <button
          type="button"
          onClick={load}
          className="flex items-center justify-center gap-1.5 rounded-card bg-light-accent px-3 py-1.5 text-xs font-semibold text-white"
        >
          <Search size={14} /> Filter
        </button>
        <label className="flex items-center gap-1 text-xs text-neutral-500 sm:col-span-3">
          From
          <input
            value={f.dateFrom}
            onChange={(e) => set("dateFrom", e.target.value)}
            type="date"
            className="rounded-card border border-neutral-300 px-2 py-1 text-xs"
          />
        </label>
        <label className="flex items-center gap-1 text-xs text-neutral-500 sm:col-span-3">
          To
          <input
            value={f.dateTo}
            onChange={(e) => set("dateTo", e.target.value)}
            type="date"
            className="rounded-card border border-neutral-300 px-2 py-1 text-xs"
          />
        </label>
      </div>

      {error && <p className="text-sm text-priority-low">{error}</p>}

      <div className="overflow-x-auto rounded-card border border-neutral-200 bg-white">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-neutral-200 text-neutral-500">
            <tr>
              <th className="px-3 py-2 font-semibold">When</th>
              <th className="px-3 py-2 font-semibold">User</th>
              <th className="px-3 py-2 font-semibold">Action</th>
              <th className="px-3 py-2 font-semibold">Target</th>
              <th className="px-3 py-2 font-semibold">Detail</th>
              <th className="px-3 py-2 text-right font-semibold">Cost</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-100">
            {rows.map((r) => (
              <tr key={r.id}>
                <td className="whitespace-nowrap px-3 py-2 text-neutral-500">
                  {r.createdAt ? new Date(r.createdAt).toLocaleString() : "-"}
                </td>
                <td className="px-3 py-2">{r.actorEmail ?? "system"}</td>
                <td className="px-3 py-2 font-medium">{r.action}</td>
                <td className="px-3 py-2 text-neutral-500">
                  {r.targetType ? `${r.targetType}` : ""}
                </td>
                <td className="px-3 py-2 text-neutral-500">
                  {r.detail ? JSON.stringify(r.detail) : ""}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {r.cost ? r.cost : ""}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-neutral-400">
                  No audit entries match.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
