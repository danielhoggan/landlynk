"use client";

import { useEffect, useState } from "react";
import { MapPin, Download, ChevronDown, SlidersHorizontal } from "lucide-react";
import { CatchmentMap } from "@/components/map/CatchmentMap";
import { RankingList } from "@/components/map/RankingList";
import { BattlecardDrawer } from "@/components/battlecard/BattlecardDrawer";
import type {
  Catchment,
  CatchmentArea,
  InputKind,
} from "@/lib/types/catchment";
import type { Battlecard } from "@/lib/types/battlecard";
import { getBattlecard, pollCatchment, submitCatchment } from "@/lib/client";
import {
  SIGNAL_TAGS,
  METRIC_FILTERS,
  areaMatchesFilters,
  type MetricKey,
  type MetricRanges,
} from "@/lib/areaTags";
import { loadSettings } from "@/lib/settings";
import { RunAssumptions } from "@/components/RunAssumptions";

// Scoring signal weights exposed in the config panel. Keys are snake_case to
// match the scoring engine (SCOPING.md Section 8).
const WEIGHT_LABELS: [string, string][] = [
  ["income_fit", "Income fit"],
  ["tenure_signal", "Tenure signal"],
  ["age_skew", "Age skew"],
  ["addressable_scale", "Addressable scale"],
  ["household_type", "Household type"],
];

// MVP entry surface: paste a postcode or grid ref, the worker builds the
// catchment, and the interactive map with ranked clickable areas renders here
// (SCOPING.md Section 3.2).
export default function HomePage() {
  const [kind, setKind] = useState<InputKind>("postcode");
  const [value, setValue] = useState("");
  const [developmentName, setDevelopmentName] = useState("");
  const [areaType, setAreaType] = useState<"MSOA" | "LA">("MSOA");
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
  const [affordability, setAffordability] = useState("4.5");
  const [showBrief, setShowBrief] = useState(false);

  // Scoring config. Weight keys are snake_case to match the scoring engine.
  // Weights are normalised server-side, so they need not sum to 1.
  const [showScoring, setShowScoring] = useState(false);
  const [overlap, setOverlap] = useState("0.10");
  const [weights, setWeights] = useState<Record<string, string>>({
    income_fit: "0.30",
    tenure_signal: "0.20",
    age_skew: "0.20",
    addressable_scale: "0.20",
    household_type: "0.10",
  });
  const setWeight = (k: string, v: string) =>
    setWeights((w) => ({ ...w, [k]: v }));

  // LA area level is opt-in (Settings). MSOA is the default and stays forced
  // off unless enabled, so the form only offers what is supported.
  const [enableLA, setEnableLA] = useState(false);

  // Seed the form from the saved default assumptions (Settings). The values
  // used are still stored per run, so this only changes new submissions.
  useEffect(() => {
    const s = loadSettings();
    setEnableLA(s.enableLA);
    if (!s.enableLA) setAreaType("MSOA");
    setAffordability(String(s.affordabilityMultiple));
    setOverlap(String(s.overlapThreshold));
    setWeights(
      Object.fromEntries(
        Object.entries(s.weights).map(([k, v]) => [k, String(v)]),
      ),
    );
  }, []);

  const splitList = (s: string) =>
    s
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);

  const [catchment, setCatchment] = useState<Catchment | null>(null);
  const [selected, setSelected] = useState<Battlecard | null>(null);
  const [selectedCode, setSelectedCode] = useState<string | undefined>();
  const [selectedName, setSelectedName] = useState<string | undefined>();
  const [drawerOpen, setDrawerOpen] = useState(false);

  const areas: CatchmentArea[] = catchment?.areas ?? [];

  // Results filters: preset signal tags plus numeric metric ranges.
  const [filter, setFilter] = useState<Set<string>>(new Set());
  const [showFilters, setShowFilters] = useState(false);
  const [rangeInputs, setRangeInputs] = useState<
    Record<string, { min: string; max: string }>
  >({});
  const toggleFilter = (id: string) =>
    setFilter((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  const setRange = (key: string, side: "min" | "max", v: string) =>
    setRangeInputs((prev) => {
      const current = prev[key] ?? { min: "", max: "" };
      return { ...prev, [key]: { ...current, [side]: v } };
    });
  const ranges: MetricRanges = {};
  for (const [key, r] of Object.entries(rangeInputs)) {
    const min = r.min === "" ? undefined : Number(r.min);
    const max = r.max === "" ? undefined : Number(r.max);
    if (min !== undefined || max !== undefined) {
      ranges[key as MetricKey] = { min, max };
    }
  }
  const activeFilterCount = filter.size + Object.keys(ranges).length;
  const filteredAreas = areas.filter((a) =>
    areaMatchesFilters(a, filter, ranges),
  );
  const matchedCodes =
    activeFilterCount === 0
      ? null
      : new Set(filteredAreas.map((a) => a.areaCode));

  const clearFilters = () => {
    setFilter(new Set());
    setRangeInputs({});
  };

  // Shortlist: starred areas the user wants combined into one export document.
  // Persisted per catchment so a selection survives a reload or revisit.
  const [starred, setStarred] = useState<Set<string>>(new Set());
  const [exporting, setExporting] = useState<"pdf" | "pptx" | null>(null);
  const starKey = catchment ? `landlynk.stars.${catchment.id}` : null;
  useEffect(() => {
    if (!starKey) return;
    try {
      const raw = window.localStorage.getItem(starKey);
      setStarred(new Set(raw ? (JSON.parse(raw) as string[]) : []));
    } catch {
      setStarred(new Set());
    }
  }, [starKey]);
  const toggleStar = (areaCode: string) =>
    setStarred((prev) => {
      const next = new Set(prev);
      if (next.has(areaCode)) next.delete(areaCode);
      else next.add(areaCode);
      if (starKey) window.localStorage.setItem(starKey, JSON.stringify([...next]));
      return next;
    });

  async function exportShortlist(format: "pdf" | "pptx") {
    if (!catchment || starred.size === 0) return;
    setExporting(format);
    try {
      const res = await fetch(
        `/api/catchments/${catchment.id}/shortlist/${format}`,
        {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ areaCodes: Array.from(starred) }),
        },
      );
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `landlynk-shortlist.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      setStatus("Could not build the shortlist export.");
    } finally {
      setExporting(null);
    }
  }

  // Reopen a saved catchment when arriving from the history view
  // (/?catchment=<id>). Served from stored data, no recompute.
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get("catchment");
    if (!id) return;
    setStatus("Loading saved catchment...");
    pollCatchment(id, setCatchment)
      .then((c) =>
        setStatus(
          c.status === "complete"
            ? `Ranked ${c.areas.length} areas.`
            : `Status: ${c.status}`,
        ),
      )
      .catch((e) =>
        setStatus(e instanceof Error ? e.message : "Failed to load"),
      );
  }, []);

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
      if (affordability) config.affordabilityMultiple = Number(affordability);
      config.overlapThreshold = Number(overlap);
      config.weights = Object.fromEntries(
        Object.entries(weights).map(([k, v]) => [k, Number(v)]),
      );

      const { id } = await submitCatchment({
        kind,
        value,
        developmentName,
        areaType,
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
    setSelectedName(area.name);
    setDrawerOpen(true);
    setSelected(null);
    try {
      setSelected(await getBattlecard(catchment.id, area.areaCode));
    } catch {
      setStatus("Could not load that Battlecard.");
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 py-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Catchment map
          </h1>
          <p className="mt-1 text-sm text-neutral-500">
            Paste a postcode or grid reference to build a ranked, clickable
            catchment.{" "}
            <a href="/how-it-works" className="font-medium text-light-accent">
              How it works
            </a>
          </p>
        </div>
      </header>

      <form
        onSubmit={onSubmit}
        className="space-y-5 rounded-card border border-neutral-200 bg-white p-5 sm:p-6"
      >
        <div className="flex items-center gap-2">
          <MapPin size={18} className="text-light-accent" />
          <h2 className="text-sm font-semibold">New catchment</h2>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <span className="mb-1.5 block text-xs font-medium text-neutral-500">
              Input type
            </span>
            <Segmented
              options={[
                { value: "postcode", label: "Postcode" },
                { value: "gridref", label: "OS grid ref" },
              ]}
              value={kind}
              onChange={(v) => setKind(v as InputKind)}
            />
          </div>
          {enableLA && (
            <div>
              <span className="mb-1.5 block text-xs font-medium text-neutral-500">
                Area level
              </span>
              <Segmented
                options={[
                  { value: "MSOA", label: "MSOA" },
                  { value: "LA", label: "LA" },
                ]}
                value={areaType}
                onChange={(v) => setAreaType(v as "MSOA" | "LA")}
              />
            </div>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field
            label="Development name"
            value={developmentName}
            onChange={setDevelopmentName}
            placeholder="e.g. Abbots Vale"
          />
          <Field
            label={kind === "postcode" ? "Postcode" : "OS grid reference"}
            value={value}
            onChange={setValue}
            placeholder={
              kind === "postcode" ? "e.g. IP14 1AA" : "e.g. TM 06457 58755"
            }
          />
        </div>

        <div className="border-t border-neutral-200 pt-4">
          <button
            type="button"
            onClick={() => setShowBrief((s) => !s)}
            className="flex w-full items-center justify-between text-sm font-medium"
          >
            <span>
              Development brief and scoring{" "}
              <span className="font-normal text-neutral-400">optional</span>
            </span>
            <ChevronDown
              size={16}
              className={`text-neutral-400 transition-transform ${showBrief ? "rotate-180" : ""}`}
            />
          </button>

          {showBrief && (
            <div className="mt-4 space-y-5">
              <div className="grid gap-4 sm:grid-cols-2">
                <Field
                  label="Town"
                  value={town}
                  onChange={setTown}
                  placeholder="Stowmarket"
                />
                <Field
                  label="Bed range"
                  value={bedRange}
                  onChange={setBedRange}
                  placeholder="2 to 5"
                />
              </div>
              <Field
                label="Strapline"
                value={strapline}
                onChange={setStrapline}
                placeholder="Room to grow"
              />
              <Field
                label="Lifestyle pillars"
                hint="comma separated"
                value={pillars}
                onChange={setPillars}
                placeholder="Connected, Green, Family"
              />
              <Field
                label="Feature bullets"
                hint="comma separated"
                value={features}
                onChange={setFeatures}
                placeholder="Open green space, Primary school nearby"
              />
              <div className="grid gap-4 sm:grid-cols-3">
                <Field
                  label="Price from"
                  prefix="£"
                  value={priceFrom}
                  onChange={setPriceFrom}
                  placeholder="280000"
                  type="number"
                />
                <Field
                  label="Price to"
                  prefix="£"
                  value={priceTo}
                  onChange={setPriceTo}
                  placeholder="450000"
                  type="number"
                />
                <Field
                  label="Drive time"
                  suffix="min"
                  value={driveTime}
                  onChange={setDriveTime}
                  placeholder="30"
                  type="number"
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                <Field
                  label="Affordability multiple"
                  suffix="×"
                  hint="income to price"
                  value={affordability}
                  onChange={setAffordability}
                  placeholder="4.5"
                  type="number"
                />
              </div>

              <div className="rounded-card bg-neutral-50 p-4">
                <button
                  type="button"
                  onClick={() => setShowScoring((s) => !s)}
                  className="flex w-full items-center justify-between text-sm font-medium"
                >
                  <span>Scoring weights</span>
                  <ChevronDown
                    size={16}
                    className={`text-neutral-400 transition-transform ${showScoring ? "rotate-180" : ""}`}
                  />
                </button>
                {showScoring && (
                  <div className="mt-4 space-y-4">
                    <p className="text-xs text-neutral-500">
                      Relative and normalised, so they need not sum to 1. Stored
                      with the catchment so the ranking stays reproducible.
                    </p>
                    <div className="grid gap-4 sm:grid-cols-2">
                      {WEIGHT_LABELS.map(([key, label]) => (
                        <Field
                          key={key}
                          label={label}
                          value={weights[key]}
                          onChange={(v) => setWeight(key, v)}
                          type="number"
                        />
                      ))}
                      <Field
                        label="Overlap threshold"
                        hint="0 to 1"
                        value={overlap}
                        onChange={setOverlap}
                        type="number"
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={busy || !value || !developmentName}
            className="w-full rounded-card bg-light-accent px-5 py-2.5 text-sm font-semibold text-white transition hover:brightness-95 disabled:opacity-50 sm:w-auto"
          >
            {busy ? "Building..." : "Build catchment"}
          </button>
          {status && <p className="text-xs text-neutral-500">{status}</p>}
        </div>
      </form>

      {catchment?.status === "complete" && areas.length === 0 && (
        <div className="rounded-card border border-priority-mid/40 bg-priority-mid/10 p-4 text-sm">
          <p className="font-semibold">No areas found in this catchment.</p>
          <p className="mt-1 text-neutral-600">
            The drive-time zone was built, but no boundaries matched. Load the
            MSOA boundaries on the{" "}
            <a href="/data" className="font-medium text-light-accent underline">
              Reference data
            </a>{" "}
            page, then build again.
          </p>
        </div>
      )}

      {catchment?.status === "complete" && areas.length > 0 && (
        <RunAssumptions config={catchment.input?.config} />
      )}

      {catchment?.status === "complete" && areas.length > 0 && (
        <div className="space-y-3 rounded-card border border-neutral-200 bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium text-neutral-500">
                Filter
              </span>
              {SIGNAL_TAGS.map((t) => {
                const active = filter.has(t.id);
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => toggleFilter(t.id)}
                    className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                      active
                        ? "bg-light-accent text-white"
                        : "border border-neutral-300 text-neutral-600 hover:bg-neutral-100"
                    }`}
                  >
                    {t.label}
                  </button>
                );
              })}
              <button
                type="button"
                onClick={() => setShowFilters((s) => !s)}
                className="flex items-center gap-1 rounded-full border border-neutral-300 px-3 py-1 text-xs font-medium text-neutral-600 hover:bg-neutral-100"
              >
                <SlidersHorizontal size={12} /> Ranges
                <ChevronDown
                  size={12}
                  className={showFilters ? "rotate-180" : ""}
                />
              </button>
              {activeFilterCount > 0 && (
                <button
                  type="button"
                  onClick={clearFilters}
                  className="text-xs font-medium text-neutral-400 hover:text-neutral-700"
                >
                  Clear
                </button>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {starred.size > 0 && (
                <>
                  <span className="text-xs font-medium text-neutral-500">
                    {starred.size} starred
                  </span>
                  <button
                    type="button"
                    onClick={() => exportShortlist("pdf")}
                    disabled={exporting !== null}
                    className="flex items-center gap-2 rounded-card bg-light-accent px-3 py-2 text-sm font-semibold text-white transition hover:brightness-95 disabled:opacity-50"
                  >
                    <Download size={16} />
                    {exporting === "pdf" ? "Building..." : "Shortlist PDF"}
                  </button>
                  <button
                    type="button"
                    onClick={() => exportShortlist("pptx")}
                    disabled={exporting !== null}
                    className="flex items-center gap-2 rounded-card border border-light-accent px-3 py-2 text-sm font-semibold text-light-accent transition hover:bg-light-accent/5 disabled:opacity-50"
                  >
                    <Download size={16} />
                    {exporting === "pptx" ? "Building..." : "Shortlist PPTX"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setStarred(new Set());
                      if (starKey) window.localStorage.removeItem(starKey);
                    }}
                    className="text-xs font-medium text-neutral-400 hover:text-neutral-700"
                  >
                    Clear stars
                  </button>
                </>
              )}
              <a
                href={`/api/catchments/${catchment.id}/kml`}
                className="flex items-center gap-2 rounded-card border border-neutral-300 px-3 py-2 text-sm font-semibold"
              >
                <Download size={16} /> Download KML
              </a>
            </div>
          </div>

          {showFilters && (
            <div className="grid gap-3 border-t border-neutral-200 pt-3 sm:grid-cols-2 lg:grid-cols-3">
              {METRIC_FILTERS.map((m) => (
                <div key={m.key}>
                  <span className="mb-1 block text-xs font-medium text-neutral-500">
                    {m.label}
                    {m.prefix ? ` (${m.prefix})` : ""}
                    {m.suffix ? ` (${m.suffix})` : ""}
                  </span>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      value={rangeInputs[m.key]?.min ?? ""}
                      onChange={(e) => setRange(m.key, "min", e.target.value)}
                      placeholder="min"
                      className="w-full rounded-card border border-neutral-300 px-2 py-1.5 text-xs outline-none focus:border-light-accent focus:ring-2 focus:ring-light-accent/20"
                    />
                    <span className="text-xs text-neutral-400">to</span>
                    <input
                      type="number"
                      value={rangeInputs[m.key]?.max ?? ""}
                      onChange={(e) => setRange(m.key, "max", e.target.value)}
                      placeholder="max"
                      className="w-full rounded-card border border-neutral-300 px-2 py-1.5 text-xs outline-none focus:border-light-accent focus:ring-2 focus:ring-light-accent/20"
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[1fr_22rem]">
        <CatchmentMap
          areas={areas}
          isochrone={catchment?.isochrone ?? null}
          coordinate={catchment?.coordinate ?? null}
          onSelectArea={onSelectArea}
          selectedAreaCode={selectedCode}
          matchedCodes={matchedCodes}
        />
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-neutral-500">
            Priority ranking
            {activeFilterCount > 0 && (
              <span className="ml-1 font-normal text-neutral-400">
                ({filteredAreas.length} of {areas.length})
              </span>
            )}
          </h2>
          {areas.length === 0 ? (
            <p className="rounded-card border border-dashed border-neutral-300 p-4 text-xs text-neutral-500">
              {busy
                ? "Scoring areas..."
                : "Build a catchment to see ranked areas here."}
            </p>
          ) : filteredAreas.length === 0 ? (
            <p className="rounded-card border border-dashed border-neutral-300 p-4 text-xs text-neutral-500">
              No areas match this filter.
            </p>
          ) : (
            <RankingList
              areas={filteredAreas}
              onSelectArea={onSelectArea}
              selectedAreaCode={selectedCode}
              starredCodes={starred}
              onToggleStar={toggleStar}
            />
          )}
        </div>
      </div>

      <BattlecardDrawer
        battlecard={selected}
        areaName={selectedName}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        pdfUrl={
          catchment && selectedCode
            ? `/api/catchments/${catchment.id}/battlecards/${selectedCode}/pdf`
            : undefined
        }
        pptxUrl={
          catchment && selectedCode
            ? `/api/catchments/${catchment.id}/battlecards/${selectedCode}/pptx`
            : undefined
        }
      />
    </div>
  );
}

function Segmented({
  options,
  value,
  onChange,
}: {
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex w-full rounded-card bg-neutral-100 p-1">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          className={`flex-1 rounded-[10px] px-3 py-1.5 text-sm font-medium transition ${
            value === o.value
              ? "bg-white text-light-accent shadow-sm"
              : "text-neutral-600 hover:text-neutral-900"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  placeholder,
  type = "text",
  hint,
  prefix,
  suffix,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: string;
  hint?: string;
  prefix?: string;
  suffix?: string;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-neutral-500">
        {label}
        {hint && (
          <span className="ml-1 font-normal text-neutral-400">{hint}</span>
        )}
      </span>
      <div className="relative">
        {prefix && (
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-neutral-400">
            {prefix}
          </span>
        )}
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className={`w-full rounded-card border border-neutral-300 bg-white py-2.5 text-sm outline-none transition focus:border-light-accent focus:ring-2 focus:ring-light-accent/20 ${
            prefix ? "pl-7 pr-3" : "px-3"
          } ${suffix ? "pr-12" : ""}`}
        />
        {suffix && (
          <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-neutral-400">
            {suffix}
          </span>
        )}
      </div>
    </label>
  );
}
