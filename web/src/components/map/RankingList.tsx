"use client";

import { Star } from "lucide-react";
import type { CatchmentArea } from "@/lib/types/catchment";
import { PRIORITY_COLORS, PRIORITY_LABELS } from "@/lib/priority";
import { tagsForArea } from "@/lib/areaTags";

interface RankingListProps {
  areas: CatchmentArea[];
  onSelectArea: (area: CatchmentArea) => void;
  selectedAreaCode?: string;
  starredCodes?: Set<string>;
  onToggleStar?: (areaCode: string) => void;
}

// The shortlist: areas ordered by priority so the user sees where to focus, not
// just the colour map (design-framework.md, the map). Keyboard reachable, and
// colour is paired with rank and label so it never relies on colour alone.
export function RankingList({
  areas,
  onSelectArea,
  selectedAreaCode,
  starredCodes,
  onToggleStar,
}: RankingListProps) {
  if (areas.length === 0) return null;
  return (
    <ol className="divide-y divide-neutral-200 overflow-hidden rounded-card border border-neutral-200">
      {areas.map((area) => {
        const selected = area.areaCode === selectedAreaCode;
        const starred = starredCodes?.has(area.areaCode) ?? false;
        return (
          <li key={area.areaCode} className="flex items-stretch">
            <button
              type="button"
              onClick={() => onSelectArea(area)}
              aria-pressed={selected}
              className={`flex min-w-0 flex-1 items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-neutral-50 ${
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
            {onToggleStar && (
              <button
                type="button"
                onClick={() => onToggleStar(area.areaCode)}
                aria-pressed={starred}
                aria-label={
                  starred
                    ? `Remove ${area.name} from shortlist`
                    : `Add ${area.name} to shortlist`
                }
                title={starred ? "Remove from shortlist" : "Add to shortlist"}
                className="flex shrink-0 items-center px-3 text-neutral-300 transition-colors hover:text-light-accent"
              >
                <Star
                  className={`h-4 w-4 ${
                    starred ? "fill-light-accent text-light-accent" : ""
                  }`}
                />
              </button>
            )}
          </li>
        );
      })}
    </ol>
  );
}
