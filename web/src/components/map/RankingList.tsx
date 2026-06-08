"use client";

import type { CatchmentArea } from "@/lib/types/catchment";
import { PRIORITY_COLORS, PRIORITY_LABELS } from "@/lib/priority";

interface RankingListProps {
  areas: CatchmentArea[];
  onSelectArea: (area: CatchmentArea) => void;
  selectedAreaCode?: string;
}

// The shortlist: areas ordered by priority so the user sees where to focus, not
// just the colour map (design-framework.md, the map). Keyboard reachable, and
// colour is paired with rank and label so it never relies on colour alone.
export function RankingList({
  areas,
  onSelectArea,
  selectedAreaCode,
}: RankingListProps) {
  if (areas.length === 0) return null;
  return (
    <ol className="divide-y divide-neutral-200 overflow-hidden rounded-card border border-neutral-200 dark:divide-neutral-800 dark:border-neutral-800">
      {areas.map((area) => {
        const selected = area.areaCode === selectedAreaCode;
        return (
          <li key={area.areaCode}>
            <button
              type="button"
              onClick={() => onSelectArea(area)}
              aria-pressed={selected}
              className={`flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-neutral-50 dark:hover:bg-neutral-900 ${
                selected ? "bg-neutral-50 dark:bg-neutral-900" : ""
              }`}
            >
              <span className="w-6 text-sm font-semibold tabular-nums text-neutral-500">
                {area.rank}
              </span>
              <span
                aria-hidden
                className="inline-block h-3 w-3 shrink-0 rounded-full"
                style={{ backgroundColor: PRIORITY_COLORS[area.band] }}
              />
              <span className="flex-1">
                <span className="block text-sm font-semibold">{area.name}</span>
                <span className="block text-xs text-neutral-500">
                  {area.areaCode} - {PRIORITY_LABELS[area.band]}
                </span>
              </span>
              <span className="text-sm font-semibold tabular-nums">
                {area.score.toFixed(2)}
              </span>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
