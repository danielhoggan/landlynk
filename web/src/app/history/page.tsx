"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { History, ChevronRight, Trash2 } from "lucide-react";
import type { CatchmentSummary } from "@/lib/types/catchment";
import { deleteCatchment, listCatchments } from "@/lib/client";

// Past catchments, read from the database so a previous run reopens without
// recompute (SCOPING.md 5.2). Each row links back to the map view and can be
// deleted.
export default function HistoryPage() {
  const [items, setItems] = useState<CatchmentSummary[] | null>(null);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    listCatchments()
      .then(setItems)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load"),
      );
  }, []);

  async function onDelete(id: string, name: string) {
    if (
      !confirm(`Delete the catchment for "${name}"? This cannot be undone.`)
    ) {
      return;
    }
    setDeleting(id);
    try {
      await deleteCatchment(id);
      setItems((prev) => (prev ? prev.filter((i) => i.id !== id) : prev));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4 py-8">
      <h1 className="flex items-center gap-2 text-lg font-semibold">
        <History size={20} /> Catchment history
      </h1>

      {error && <p className="text-sm text-priority-low">{error}</p>}
      {items === null && !error && (
        <p className="text-sm text-neutral-500">Loading...</p>
      )}
      {items && items.length === 0 && (
        <p className="text-sm text-neutral-500">
          No catchments yet. Build one from the map view.
        </p>
      )}

      {items && items.length > 0 && (
        <ol className="divide-y divide-neutral-200 overflow-hidden rounded-card border border-neutral-200">
          {items.map((item) => (
            <li key={item.id} className="flex items-center">
              <Link
                href={`/?catchment=${item.id}`}
                className="flex flex-1 items-center gap-3 px-4 py-3 transition-colors hover:bg-neutral-50"
              >
                <span className="flex-1">
                  <span className="block text-sm font-semibold">
                    {item.developmentName}
                  </span>
                  <span className="block text-xs text-neutral-500">
                    {item.inputValue} - {item.status} - {item.areaCount} areas
                    {item.createdAt
                      ? ` - ${new Date(item.createdAt).toLocaleDateString("en-GB")}`
                      : ""}
                  </span>
                </span>
                <ChevronRight size={18} className="text-neutral-400" />
              </Link>
              <button
                type="button"
                onClick={() => onDelete(item.id, item.developmentName)}
                disabled={deleting === item.id}
                aria-label={`Delete ${item.developmentName}`}
                className="px-3 py-3 text-neutral-400 transition-colors hover:text-priority-low disabled:opacity-50"
              >
                <Trash2 size={16} />
              </button>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
