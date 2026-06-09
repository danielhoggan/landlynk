"use client";

import { useEffect, useState } from "react";
import { getReferenceHealth, type ReferenceHealth } from "@/lib/client";

const STYLE: Record<string, { dot: string; label: string }> = {
  green: { dot: "bg-priority-high", label: "Reference data fully loaded" },
  amber: { dot: "bg-priority-mid", label: "Reference data partly loaded" },
  red: { dot: "bg-priority-low", label: "Reference data not loaded" },
};

// A RAG status dot for reference data, shown to every user. Detail (sources,
// per dataset) stays on the admin-only Reference data page.
export function ReferenceStatusDot() {
  const [health, setHealth] = useState<ReferenceHealth | null>(null);

  useEffect(() => {
    getReferenceHealth()
      .then(setHealth)
      .catch(() => setHealth({ state: "red", loaded: 0, total: 0 }));
  }, []);

  if (!health) return null;
  const style = STYLE[health.state] ?? STYLE.red;
  const title = `${style.label} (${health.loaded}/${health.total} datasets)`;

  return (
    <div
      className="flex items-center gap-2 px-2 text-xs text-neutral-500"
      title={title}
    >
      <span className={`h-2.5 w-2.5 rounded-full ${style.dot}`} aria-hidden />
      <span>
        Data{" "}
        {health.state === "green"
          ? "ready"
          : health.state === "amber"
            ? `${health.loaded}/${health.total}`
            : "unavailable"}
      </span>
    </div>
  );
}
