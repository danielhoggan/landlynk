"use client";

import type { CatchmentArea } from "@/lib/types/catchment";
import { PRIORITY_COLORS } from "@/lib/priority";

interface CatchmentMapProps {
  areas: CatchmentArea[];
  onSelectArea: (area: CatchmentArea) => void;
  selectedAreaCode?: string;
}

// The interactive catchment map is the centrepiece (design-framework.md, the
// map). It uses open-source tiles via MapLibre GL: no licensed tiles. The
// drive-time isochrone is drawn as a translucent overlay so the boundary stays
// visible, and each MSOA is a clickable region colour-coded by priority band.
//
// This is the scaffold seam: the MapLibre GL instance, the isochrone overlay
// layer and the per-area fill layers are wired here. Until live data and tiles
// are connected it renders the area set as an accessible, keyboard-reachable
// fallback so the surrounding flow can be built and tested.
export function CatchmentMap({
  areas,
  onSelectArea,
  selectedAreaCode,
}: CatchmentMapProps) {
  return (
    <div className="relative h-[60vh] min-h-[360px] w-full overflow-hidden rounded-card border border-neutral-200 bg-neutral-100 dark:border-neutral-800 dark:bg-neutral-900">
      <div className="absolute left-3 top-3 z-10 rounded-card bg-white/80 px-3 py-1.5 text-xs font-medium text-neutral-600 frosted dark:bg-black/60 dark:text-neutral-300">
        MapLibre GL canvas. Isochrone overlay and clickable regions mount here.
      </div>

      {/* Accessible fallback: keyboard-reachable region list mirroring the map
          regions until tiles and geometry are wired. */}
      <ul className="grid h-full grid-cols-2 content-start gap-2 overflow-y-auto p-4 pt-14 sm:grid-cols-3">
        {areas.map((area) => {
          const selected = area.areaCode === selectedAreaCode;
          return (
            <li key={area.areaCode}>
              <button
                type="button"
                onClick={() => onSelectArea(area)}
                aria-pressed={selected}
                className={`flex w-full flex-col items-start gap-1 rounded-card border p-3 text-left transition-colors ${
                  selected
                    ? "border-light-accent dark:border-dark-accent"
                    : "border-neutral-200 dark:border-neutral-700"
                } bg-white dark:bg-neutral-950`}
              >
                <span className="flex items-center gap-2 text-sm font-semibold">
                  <span
                    aria-hidden
                    className="inline-block h-3 w-3 rounded-full"
                    style={{ backgroundColor: PRIORITY_COLORS[area.band] }}
                  />
                  #{area.rank} {area.name}
                </span>
                <span className="text-xs text-neutral-500">
                  {area.areaCode} - score {area.score.toFixed(2)}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
