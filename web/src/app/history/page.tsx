"use client";

import { useEffect, useState } from "react";
import { History } from "lucide-react";
import type { CatchmentSummary } from "@/lib/types/catchment";
import { listCatchments } from "@/lib/client";
import { useUser } from "@/lib/userContext";
import { CatchmentList } from "@/components/history/CatchmentList";

// Past catchments, private to the signed-in user plus any shared with them.
// Reopen a run without recompute. Archive to hide; admins can delete.
export default function HistoryPage() {
  const { isAdmin } = useUser();
  const [items, setItems] = useState<CatchmentSummary[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    listCatchments(false)
      .then(setItems)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load"),
      );
  }, []);

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4">
      <h1 className="flex items-center gap-2 text-lg font-semibold">
        <History size={20} /> Previous catchments
      </h1>

      {error && <p className="text-sm text-priority-low">{error}</p>}
      {items === null && !error && (
        <p className="text-sm text-neutral-500">Loading...</p>
      )}
      {items && items.length === 0 && (
        <p className="text-sm text-neutral-500">
          No catchments yet. Build one from the map view. Runs you create are
          private to you; share them with colleagues from here.
        </p>
      )}

      {items && items.length > 0 && (
        <CatchmentList
          items={items}
          mode="active"
          isAdmin={isAdmin}
          onChanged={(id) =>
            setItems((prev) => (prev ? prev.filter((i) => i.id !== id) : prev))
          }
          onError={setError}
        />
      )}
    </div>
  );
}
