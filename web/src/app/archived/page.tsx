"use client";

import { useEffect, useState } from "react";
import { Archive } from "lucide-react";
import type { CatchmentSummary } from "@/lib/types/catchment";
import { listCatchments } from "@/lib/client";
import { useUser } from "@/lib/userContext";
import { CatchmentList } from "@/components/history/CatchmentList";

// Archived runs: hidden from the main history but never destroyed. Restore one
// to bring it back; admins can delete permanently.
export default function ArchivedPage() {
  const { isAdmin } = useUser();
  const [items, setItems] = useState<CatchmentSummary[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    listCatchments(true)
      .then(setItems)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load"),
      );
  }, []);

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4">
      <h1 className="flex items-center gap-2 text-lg font-semibold">
        <Archive size={20} /> Archived catchments
      </h1>

      {error && <p className="text-sm text-priority-low">{error}</p>}
      {items === null && !error && (
        <p className="text-sm text-neutral-500">Loading...</p>
      )}
      {items && items.length === 0 && (
        <p className="text-sm text-neutral-500">
          Nothing archived. Archive a run from the history to tuck it away here
          without deleting it.
        </p>
      )}

      {items && items.length > 0 && (
        <CatchmentList
          items={items}
          mode="archived"
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
