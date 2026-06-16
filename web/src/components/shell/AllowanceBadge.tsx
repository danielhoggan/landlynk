"use client";

import { useEffect, useState } from "react";
import { Coins, Play } from "lucide-react";
import { getUsage, type LlmUsage, type UsageAllowance } from "@/lib/client";
import { useUser } from "@/lib/userContext";

// Persistent allowance indicator for external (metered) users: the monthly AI
// lookups and catchment runs left, and when they refresh. Internal users and
// admins are unmetered, so it renders nothing for them. Refetches when the
// active brand changes, since allowances are pooled per the active brand's group.
export function AllowanceBadge() {
  const { activeBrand } = useUser();
  const [usage, setUsage] = useState<LlmUsage | null>(null);

  useEffect(() => {
    getUsage()
      .then(setUsage)
      .catch(() => {});
  }, [activeBrand?.builderId]);

  const showAi = usage?.metered === true;
  const showJobs = usage?.jobs?.metered === true;
  if (!showAi && !showJobs) return null;

  return (
    <div className="flex flex-col gap-1.5 px-2 text-xs">
      {showAi && (
        <AllowanceLine
          icon={<Coins size={14} aria-hidden className="shrink-0" />}
          allowance={usage as UsageAllowance}
          noun="AI lookup"
          title="Your AI lookup allowance this month"
        />
      )}
      {showJobs && (
        <AllowanceLine
          icon={<Play size={14} aria-hidden className="shrink-0" />}
          allowance={usage!.jobs as UsageAllowance}
          noun="run"
          title="Your catchment run allowance this month"
        />
      )}
    </div>
  );
}

function AllowanceLine({
  icon,
  allowance,
  noun,
  title,
}: {
  icon: React.ReactNode;
  allowance: UsageAllowance;
  noun: string;
  title: string;
}) {
  const plural = `${noun}s`;
  const left =
    allowance.cap == null
      ? `${allowance.used ?? 0} ${plural} used`
      : `${allowance.remaining ?? 0} of ${allowance.cap} ${plural} left`;
  const resets = allowance.resetsOn
    ? new Date(allowance.resetsOn).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
      })
    : null;
  const exhausted =
    allowance.cap != null &&
    allowance.remaining != null &&
    allowance.remaining <= 0;

  return (
    <div title={title}>
      <div
        className={`flex items-center gap-2 ${
          exhausted ? "text-priority-low" : "text-neutral-500"
        }`}
      >
        {icon}
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
