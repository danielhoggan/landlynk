"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, X } from "lucide-react";
import { getReferenceHealth } from "@/lib/client";
import { useUser } from "@/lib/userContext";

// Friendly dataset names for the warning, matching the Reference data cards.
const NAMES: Record<string, string> = {
  geo_boundaries: "Area boundaries",
  census_demographics: "Census demographics",
  census_tenure: "Census tenure",
  income_estimates: "Income estimates",
  house_prices: "House prices",
  green_space: "Green space",
  imd: "Deprivation (IMD)",
  schools: "Schools",
  crime: "Crime",
  postcodes: "Postcodes",
  hospitals: "Hospitals",
};

const DISMISS_KEY = "landlynk.staleDismissed";

// Admin-only banner: when loaded reference datasets are older than their refresh
// cadence, nudge an admin to check the source for a newer release and reload.
// Dismissible for the session so it does not nag.
export function ReferenceWarning() {
  const { isAdmin } = useUser();
  const [stale, setStale] = useState<string[]>([]);
  const [dismissed, setDismissed] = useState(true);

  useEffect(() => {
    if (!isAdmin) return;
    getReferenceHealth()
      .then((h) => {
        const s = h.stale ?? [];
        setStale(s);
        const seen = window.sessionStorage.getItem(DISMISS_KEY) === s.join(",");
        setDismissed(seen || s.length === 0);
      })
      .catch(() => {});
  }, [isAdmin]);

  if (!isAdmin || dismissed || stale.length === 0) return null;

  return (
    <div className="flex items-start gap-3 border-b border-priority-mid/40 bg-priority-mid/10 px-4 py-2.5 text-sm">
      <AlertTriangle size={18} className="mt-0.5 shrink-0 text-priority-mid" />
      <p className="flex-1 text-neutral-700">
        Reference data may be out of date:{" "}
        <span className="font-semibold">
          {stale.map((k) => NAMES[k] ?? k).join(", ")}
        </span>
        . Check the source for a newer release and reload on the{" "}
        <a href="/data" className="font-semibold text-light-accent underline">
          Reference data
        </a>{" "}
        page.
      </p>
      <button
        type="button"
        onClick={() => {
          window.sessionStorage.setItem(DISMISS_KEY, stale.join(","));
          setDismissed(true);
        }}
        aria-label="Dismiss"
        className="shrink-0 text-neutral-400 hover:text-neutral-700"
      >
        <X size={16} />
      </button>
    </div>
  );
}
