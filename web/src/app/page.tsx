"use client";

import { useState } from "react";
import { MapPin } from "lucide-react";
import { TabStrip } from "@/components/shell/TabStrip";
import { CatchmentMap } from "@/components/map/CatchmentMap";
import { BattlecardDrawer } from "@/components/battlecard/BattlecardDrawer";
import type { CatchmentArea, InputKind } from "@/lib/types/catchment";
import type { Battlecard } from "@/lib/types/battlecard";

// MVP entry surface: the user pastes a postcode or grid ref, the worker builds
// the catchment, and the interactive map with ranked clickable areas renders
// here (SCOPING.md Section 3.2). This page wires the flow; live data arrives
// once the worker and reference tables are connected.
export default function HomePage() {
  const [kind, setKind] = useState<InputKind>("postcode");
  const [value, setValue] = useState("");
  const [developmentName, setDevelopmentName] = useState("");
  const [status, setStatus] = useState<string>("");
  const [areas, setAreas] = useState<CatchmentArea[]>([]);
  const [selected, setSelected] = useState<Battlecard | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("Submitting catchment job...");
    try {
      const res = await fetch("/api/catchments", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ kind, value, developmentName }),
      });
      if (!res.ok) {
        setStatus(`Job submission failed: ${res.status}`);
        return;
      }
      const { id } = (await res.json()) as { id: string };
      setStatus(`Job ${id} queued. The map updates when scoring completes.`);
    } catch {
      setStatus("Could not reach the API. Is the worker running?");
    }
  }

  function onSelectArea(area: CatchmentArea) {
    // In the live flow this fetches the stored Battlecard for the area.
    setStatus(`Selected ${area.name}. Loading Battlecard...`);
    setDrawerOpen(true);
  }

  return (
    <div className="mx-auto max-w-5xl">
      <TabStrip tabs={["Input", "Map", "Ranking", "Exports"]} />

      <div className="space-y-6 p-4">
        <form
          onSubmit={onSubmit}
          className="space-y-4 rounded-card border border-neutral-200 p-5 dark:border-neutral-800"
        >
          <h1 className="flex items-center gap-2 text-lg font-semibold">
            <MapPin size={20} /> New catchment
          </h1>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setKind("postcode")}
              className={`rounded-card px-3 py-1.5 text-sm font-medium ${
                kind === "postcode"
                  ? "bg-light-accent text-white dark:bg-dark-accent"
                  : "border border-neutral-300 dark:border-neutral-700"
              }`}
            >
              Postcode
            </button>
            <button
              type="button"
              onClick={() => setKind("gridref")}
              className={`rounded-card px-3 py-1.5 text-sm font-medium ${
                kind === "gridref"
                  ? "bg-light-accent text-white dark:bg-dark-accent"
                  : "border border-neutral-300 dark:border-neutral-700"
              }`}
            >
              OS grid ref
            </button>
          </div>

          <input
            value={developmentName}
            onChange={(e) => setDevelopmentName(e.target.value)}
            placeholder="Development name"
            className="w-full rounded-card border border-neutral-300 bg-transparent px-3 py-2 text-sm dark:border-neutral-700"
          />
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={kind === "postcode" ? "e.g. IP14 1AA" : "e.g. TM 06457 58755"}
            className="w-full rounded-card border border-neutral-300 bg-transparent px-3 py-2 text-sm dark:border-neutral-700"
          />
          <button
            type="submit"
            className="rounded-card bg-light-accent px-4 py-2 text-sm font-semibold text-white dark:bg-dark-accent"
          >
            Build catchment
          </button>

          {status && <p className="text-xs text-neutral-500">{status}</p>}
        </form>

        <CatchmentMap
          areas={areas}
          onSelectArea={onSelectArea}
          selectedAreaCode={selected?.areaCode}
        />
      </div>

      <BattlecardDrawer
        battlecard={selected}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
      />
    </div>
  );
}
