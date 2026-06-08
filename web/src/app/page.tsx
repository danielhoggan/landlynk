"use client";

import { useState } from "react";
import { MapPin } from "lucide-react";
import { CatchmentMap } from "@/components/map/CatchmentMap";
import { RankingList } from "@/components/map/RankingList";
import { BattlecardDrawer } from "@/components/battlecard/BattlecardDrawer";
import type { Catchment, CatchmentArea, InputKind } from "@/lib/types/catchment";
import type { Battlecard } from "@/lib/types/battlecard";
import { getBattlecard, pollCatchment, submitCatchment } from "@/lib/client";

// MVP entry surface: paste a postcode or grid ref, the worker builds the
// catchment, and the interactive map with ranked clickable areas renders here
// (SCOPING.md Section 3.2).
export default function HomePage() {
  const [kind, setKind] = useState<InputKind>("postcode");
  const [value, setValue] = useState("");
  const [developmentName, setDevelopmentName] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  // Development brief and scoring inputs. These shape the Battlecard header and
  // the priority score, so a real run reflects the scheme not the defaults.
  const [town, setTown] = useState("");
  const [strapline, setStrapline] = useState("");
  const [pillars, setPillars] = useState("");
  const [features, setFeatures] = useState("");
  const [priceFrom, setPriceFrom] = useState("");
  const [priceTo, setPriceTo] = useState("");
  const [bedRange, setBedRange] = useState("");
  const [driveTime, setDriveTime] = useState("30");
  const [showBrief, setShowBrief] = useState(false);

  const splitList = (s: string) =>
    s.split(",").map((x) => x.trim()).filter(Boolean);

  const [catchment, setCatchment] = useState<Catchment | null>(null);
  const [selected, setSelected] = useState<Battlecard | null>(null);
  const [selectedCode, setSelectedCode] = useState<string | undefined>();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const areas: CatchmentArea[] = catchment?.areas ?? [];

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setCatchment(null);
    setStatus("Submitting catchment job...");
    try {
      const config: Record<string, unknown> = {};
      if (priceFrom && priceTo) {
        config.priceBand = { from: Number(priceFrom), to: Number(priceTo) };
      }
      if (bedRange) config.bedRange = bedRange;
      if (driveTime) config.driveTimeMinutes = Number(driveTime);

      const { id } = await submitCatchment({
        kind,
        value,
        developmentName,
        town: town || undefined,
        strapline: strapline || undefined,
        lifestylePillars: splitList(pillars),
        developmentFeatures: splitList(features),
        config: Object.keys(config).length ? config : undefined,
      });
      setStatus("Building catchment. Geocoding, isochrone, scoring...");
      const final = await pollCatchment(id, (c) => {
        setCatchment(c);
        setStatus(`Status: ${c.status}`);
      });
      setStatus(
        final.status === "complete"
          ? `Ranked ${final.areas.length} areas.`
          : `Job failed: ${final.error ?? "unknown error"}`,
      );
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  async function onSelectArea(area: CatchmentArea) {
    if (!catchment) return;
    setSelectedCode(area.areaCode);
    setDrawerOpen(true);
    setSelected(null);
    try {
      setSelected(await getBattlecard(catchment.id, area.areaCode));
    } catch {
      setStatus("Could not load that Battlecard.");
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4">
      <form
        onSubmit={onSubmit}
        className="space-y-4 rounded-card border border-neutral-200 p-5 dark:border-neutral-800"
      >
        <h1 className="flex items-center gap-2 text-lg font-semibold">
          <MapPin size={20} /> New catchment
        </h1>

        <div className="flex gap-2">
          {(["postcode", "gridref"] as InputKind[]).map((k) => (
            <button
              key={k}
              type="button"
              onClick={() => setKind(k)}
              className={`rounded-card px-3 py-1.5 text-sm font-medium ${
                kind === k
                  ? "bg-light-accent text-white dark:bg-dark-accent"
                  : "border border-neutral-300 dark:border-neutral-700"
              }`}
            >
              {k === "postcode" ? "Postcode" : "OS grid ref"}
            </button>
          ))}
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
          type="button"
          onClick={() => setShowBrief((s) => !s)}
          className="text-xs font-medium text-light-accent dark:text-dark-accent"
        >
          {showBrief ? "Hide" : "Add"} development brief and scoring
        </button>

        {showBrief && (
          <div className="space-y-3 rounded-card border border-neutral-200 p-4 dark:border-neutral-800">
            <div className="grid grid-cols-2 gap-3">
              <Field label="Town" value={town} onChange={setTown} placeholder="Stowmarket" />
              <Field label="Bed range" value={bedRange} onChange={setBedRange} placeholder="2 to 5" />
            </div>
            <Field label="Strapline" value={strapline} onChange={setStrapline} placeholder="Room to grow" />
            <Field
              label="Lifestyle pillars (comma separated)"
              value={pillars}
              onChange={setPillars}
              placeholder="Connected, Green, Family"
            />
            <Field
              label="Feature bullets (comma separated)"
              value={features}
              onChange={setFeatures}
              placeholder="Open green space, Primary school nearby"
            />
            <div className="grid grid-cols-3 gap-3">
              <Field label="Price from (£)" value={priceFrom} onChange={setPriceFrom} placeholder="280000" type="number" />
              <Field label="Price to (£)" value={priceTo} onChange={setPriceTo} placeholder="450000" type="number" />
              <Field label="Drive time (min)" value={driveTime} onChange={setDriveTime} placeholder="30" type="number" />
            </div>
          </div>
        )}

        <button
          type="submit"
          disabled={busy || !value || !developmentName}
          className="rounded-card bg-light-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 dark:bg-dark-accent"
        >
          {busy ? "Building..." : "Build catchment"}
        </button>

        {status && <p className="text-xs text-neutral-500">{status}</p>}
      </form>

      <div className="grid gap-4 lg:grid-cols-[1fr_22rem]">
        <CatchmentMap
          areas={areas}
          isochrone={catchment?.isochrone ?? null}
          coordinate={catchment?.coordinate ?? null}
          onSelectArea={onSelectArea}
          selectedAreaCode={selectedCode}
        />
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-neutral-500">Priority ranking</h2>
          <RankingList
            areas={areas}
            onSelectArea={onSelectArea}
            selectedAreaCode={selectedCode}
          />
        </div>
      </div>

      <BattlecardDrawer
        battlecard={selected}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        pdfUrl={
          catchment && selectedCode
            ? `/api/catchments/${catchment.id}/battlecards/${selectedCode}/pdf`
            : undefined
        }
      />
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-neutral-500">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-card border border-neutral-300 bg-transparent px-3 py-2 text-sm dark:border-neutral-700"
      />
    </label>
  );
}
