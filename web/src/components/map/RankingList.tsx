"use client";

import type { CatchmentArea } from "@/lib/types/catchment";
import { PRIORITY_COLORS, PRIORITY_LABELS } from "@/lib/priority";
import { tagsForArea } from "@/lib/areaTags";

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
    <ol className="divide-y divide-neutral-200 overflow-hidden rounded-card border border-neutral-200">
      {areas.map((area) => {
        const selected = area.areaCode === selectedAreaCode;
        return (
          <li key={area.areaCode}>
            <button
              type="button"
              onClick={() => onSelectArea(area)}
              aria-pressed={selected}
              className={`flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-neutral-50 ${
                selected ? "bg-neutral-50" : ""
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
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-semibold">
                  {area.name}
                </span>
                <span className="block text-xs text-neutral-500">
                  {PRIORITY_LABELS[area.band]}
                </span>
                {tagsForArea(area).length > 0 && (
                  <span className="mt-1 flex flex-wrap gap-1">
                    {tagsForArea(area).map((t) => (
                      <span
                        key={t.id}
                        className="rounded-full bg-light-accent/10 px-1.5 py-0.5 text-[10px] font-medium text-light-accent"
                      >
                        {t.label}
                      </span>
                    ))}
                  </span>
                )}
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
