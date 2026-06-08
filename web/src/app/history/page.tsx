"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { History, ChevronRight } from "lucide-react";
import type { CatchmentSummary } from "@/lib/types/catchment";
import { listCatchments } from "@/lib/client";

// Past catchments, read from the database so a previous run reopens without
// recompute (SCOPING.md 5.2). Each row links back to the map view.
export default function HistoryPage() {
  const [items, setItems] = useState<CatchmentSummary[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    listCatchments()
      .then(setItems)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load"),
      );
  }, []);

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4">
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
            <li key={item.id}>
              <Link
                href={`/?catchment=${item.id}`}
                className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-neutral-50"
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
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
