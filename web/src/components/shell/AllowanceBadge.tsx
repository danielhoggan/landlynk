"use client";

import { useEffect, useState } from "react";
import { Coins } from "lucide-react";
import { getUsage, type LlmUsage } from "@/lib/client";

// Persistent AI allowance indicator for external (metered) users: lookups left
// this month and when the allowance refreshes. Internal users and admins are
// unmetered, so it renders nothing for them.
export function AllowanceBadge() {
  const [usage, setUsage] = useState<LlmUsage | null>(null);

  useEffect(() => {
    getUsage()
      .then(setUsage)
      .catch(() => {});
  }, []);

  if (!usage?.metered) return null;

  const left =
    usage.cap == null
      ? `${usage.used ?? 0} AI lookups used`
      : `${usage.remaining ?? 0} of ${usage.cap} AI lookups left`;
  const resets = usage.resetsOn
    ? new Date(usage.resetsOn).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
      })
    : null;
  const exhausted =
    usage.cap != null && usage.remaining != null && usage.remaining <= 0;

  return (
    <div
      className="px-2 text-xs"
      title="Your AI lookup allowance this month"
    >
      <div
        className={`flex items-center gap-2 ${
          exhausted ? "text-priority-low" : "text-neutral-500"
        }`}
      >
        <Coins size={14} aria-hidden className="shrink-0" />
        <span>{left}</span>
      </div>
      {resets && (
        <p className="mt-0.5 pl-6 text-[11px] text-neutral-400">
          Refreshes {resets}
        </p>
      )}
    </div>
  );
}
