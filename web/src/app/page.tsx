"use client";

import { useEffect, useState } from "react";
import { Download, ChevronDown, SlidersHorizontal } from "lucide-react";
import { CatchmentMap } from "@/components/map/CatchmentMap";
import { RankingList } from "@/components/map/RankingList";
import { BattlecardDrawer } from "@/components/battlecard/BattlecardDrawer";
import type {
  Catchment,
  CatchmentArea,
  InputKind,
} from "@/lib/types/catchment";
import type { Battlecard } from "@/lib/types/battlecard";
import {
  combinedExport,
  reportExport,
  getBattlecard,
  getBuilderProfiles,
  getCatchmentSites,
  pollCatchment,
  submitCatchment,
  type BuilderProfile,
  type DevelopmentSite,
} from "@/lib/client";
import {
  SIGNAL_TAGS,
  METRIC_FILTERS,
  areaMatchesFilters,
  buildTagContext,
  type MetricKey,
  type MetricRanges,
} from "@/lib/areaTags";
import { loadSettings } from "@/lib/settings";
import { RunAssumptions } from "@/components/RunAssumptions";
import { AreaProfilePanel } from "@/components/AreaProfilePanel";
import { IntentCards, type Intent } from "@/components/IntentCards";
import { VerdictPanel, MixPanel } from "@/components/AppraisalPanels";
import { segmentsForIndustry } from "@/lib/segments";
import { INDUSTRIES } from "@/lib/industries";
import { OBJECTIVES, SIGNAL_LABELS } from "@/lib/objectives";
import { useUser } from "@/lib/userContext";

// MVP entry surface: paste a postcode or grid ref, the worker builds the
// catchment, and the interactive map with ranked clickable areas renders here
// (SCOPING.md Section 3.2).
export default function HomePage() {
  const { isAdmin, activeBrand } = useUser();
  // Internal users and admins have no brand, so they pick a sector here; branded
  // users inherit their brand's industry. The effective industry drives the
  // segments and the housebuilder intents.
  const [pickedIndustry, setPickedIndustry] = useState("");
  const effectiveIndustry = activeBrand?.industry ?? (pickedIndustry || null);
  const segmentOptions = segmentsForIndustry(effectiveIndustry);
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
  const [segment, setSegment] = useState("");
  // Business objective: what the catchment is for. Reweights the signals and
  // frames the AI commentary. Empty keeps the default home-sales weights.
  const [objective, setObjective] = useState("");
  // The selected brand's best/target locations, and whether to weight the
  // ranking toward areas resembling them (lookalike signal).
  const [brandLocations, setBrandLocations] = useState<string[]>([]);
  const [useLookalike, setUseLookalike] = useState(false);
  const [profiles, setProfiles] = useState<BuilderProfile[]>([]);
  const [profileId, setProfileId] = useState("");
  const [brandHeading, setBrandHeading] = useState("");
  const [brandTheme, setBrandTheme] = useState<{
    secondary?: string;
    accent?: string;
    logoPath?: string;
  }>({});
  const [driveTime, setDriveTime] = useState("30");
  const [catchmentMode, setCatchmentMode] = useState<"driveTime" | "radius">(
    "driveTime",
  );
  const [radiusKm, setRadiusKm] = useState("1.5");
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

  // Choosing an objective pre-fills the scoring weights with its preset (the
  // user can still tune them) and applies its default segment when set.
  function applyObjective(id: string) {
    setObjective(id);
    const obj = OBJECTIVES.find((o) => o.id === id);
    if (!obj) return;
    setWeights(
      Object.fromEntries(
        Object.entries(obj.weights).map(([k, v]) => [k, String(v)]),
      ),
    );
    if (obj.segment && !segment) setSegment(obj.segment);
  }

  // Toggle the lookalike signal: add or remove its weight so it shows in the
  // (dynamic) weights editor and contributes to scoring only when on.
  function toggleLookalike(on: boolean) {
    setUseLookalike(on);
    setWeights((w) => {
      const next = { ...w };
      if (on) next.lookalike = next.lookalike ?? "0.25";
      else delete next.lookalike;
      return next;
    });
  }

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

  // Builder profiles the signed-in user may use (scoped to their group if
  // external). Selecting one fills the brief and themes the exports.
  useEffect(() => {
    getBuilderProfiles()
      .then(setProfiles)
      .catch(() => setProfiles([]));
  }, []);

  function applyProfile(id: string) {
    setProfileId(id);
    const p = profiles.find((x) => x.id === id);
    if (!p) {
      setBrandHeading("");
      setBrandTheme({});
      setBrandLocations([]);
      toggleLookalike(false);
      return;
    }
    setBrandLocations(p.targetLocations ?? []);
    if (!p.targetLocations?.length) toggleLookalike(false);
    if (p.segment) setSegment(p.segment);
    if (p.bedRange) setBedRange(p.bedRange);
    if (p.priceFrom != null) setPriceFrom(String(p.priceFrom));
    if (p.priceTo != null) setPriceTo(String(p.priceTo));
    if (p.strapline) setStrapline(p.strapline);
    if (p.pillars?.length) setPillars(p.pillars.join(", "));
    if (p.features?.length) setFeatures(p.features.join(", "));
    setBrandHeading(p.themeHeading ?? "");
    setBrandTheme({
      secondary: p.themeSecondary ?? undefined,
      accent: p.themeAccent ?? undefined,
      logoPath: p.logoPath ?? undefined,
    });
  }

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
  // The new-catchment form. Shown by default (the page is "New catchment"), then
  // collapsed once a run completes so its title and map lead, not the form.
  const [showForm, setShowForm] = useState(true);
  // Housebuilder intent (signposted on the New catchment page). "find_site" is
  // audience-led discovery; "appraise" is the default single-site flow.
  const [intent, setIntent] = useState<Intent>("appraise");
  // Brownfield development sites overlaid on the map for Find a site.
  const [sites, setSites] = useState<DevelopmentSite[]>([]);
  // Find a site: weight the ranking toward areas with more brownfield capacity.
  const [weightByLand, setWeightByLand] = useState(false);
  // Find a site: order the ranking by audience fit (score) or by buildable land.
  const [rankSort, setRankSort] = useState<"fit" | "land">("fit");

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
  const tagContext = buildTagContext(areas);
  const filteredAreas = areas.filter((a) =>
    areaMatchesFilters(a, filter, ranges, tagContext),
  );
  const matchedCodes =
    activeFilterCount === 0
      ? null
      : new Set(filteredAreas.map((a) => a.areaCode));

  const clearFilters = () => {
    setFilter(new Set());
    setRangeInputs({});
  };

  // Housebuilder intents are signposted only for residential brands; everyone
  // else keeps the single, generic flow.
  const isHousebuilder = effectiveIndustry === "residential";
  const audienceLabel = segmentOptions.find((s) => s.id === segment)?.label;
  // Find-a-site needs a target audience and a search location; the other flows
  // need a development name and a location.
  // Find a site needs an audience; the others just need a location (the site
  // name is optional).
  const canSubmit =
    intent === "find_site" ? Boolean(value && segment) : Boolean(value);

  function chooseIntent(next: Intent) {
    setIntent(next);
    // Find a site ranks by audience fit and development potential, so it weights
    // the segment-driven signals (age, tenure, household) alongside scale, not
    // the land objective's demand-only preset which ignores age and tenure and
    // so would rank every audience identically. The land objective still frames
    // the commentary.
    if (next === "find_site") {
      setObjective("land_acquisition");
      setWeights({
        age_skew: "0.25",
        tenure_signal: "0.20",
        household_type: "0.15",
        addressable_scale: "0.25",
        income_fit: "0.15",
      });
    }
  }

  // Read from the run's stored config, so the drawer reflects what the run
  // actually used: whether a price was set and which audience it searched for.
  // Brownfield plots grouped by area, for the Find a site ranking badges.
  const plotsByArea = sites.reduce<Record<string, { count: number; homes: number }>>(
    (acc, s) => {
      if (!s.areaCode) return acc;
      const cur = acc[s.areaCode] ?? { count: 0, homes: 0 };
      cur.count += 1;
      cur.homes += s.maxDwellings ?? 0;
      acc[s.areaCode] = cur;
      return acc;
    },
    {},
  );

  // Find a site can lead with the most buildable land instead of pure fit.
  const rankedAreas =
    intent === "find_site" && rankSort === "land"
      ? [...filteredAreas].sort(
          (a, b) =>
            (plotsByArea[b.areaCode]?.homes ?? 0) -
            (plotsByArea[a.areaCode]?.homes ?? 0),
        )
      : filteredAreas;

  const runConfig = catchment?.input?.config;
  const runPriceSet = Boolean(runConfig?.priceBand?.from);
  const runAudienceLabel = runConfig?.segment
    ? (segmentOptions.find((s) => s.id === runConfig.segment)?.label ?? null)
    : null;

  // A completed run that has areas. Its title leads the page (development name
  // and the postcode or grid ref entered), falling back to the input alone.
  const activeRun = catchment?.status === "complete" && areas.length > 0;
  const runTitle =
    [catchment?.input?.developmentName?.trim(), catchment?.input?.value?.trim()]
      .filter(Boolean)
      .join(" · ") || "Catchment";

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

  // Combine areas into one aggregate Battlecard: the starred selection, or the
  // whole catchment. Distinct from the shortlist deck (one slide per area).
  const [combining, setCombining] = useState<string | null>(null);
  async function exportCombined(
    format: "pdf" | "pptx",
    scope: "selection" | "whole",
  ) {
    if (!catchment) return;
    setCombining(`${scope}-${format}`);
    try {
      const blob = await combinedExport(catchment.id, format, {
        scope,
        areaCodes: scope === "selection" ? Array.from(starred) : undefined,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `landlynk-combined.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      setStatus("Could not build the combined Battlecard.");
    } finally {
      setCombining(null);
    }
  }

  // The full multi-slide report deck (the LA Insight equivalent), for the whole
  // catchment or the starred selection.
  async function exportReport(scope: "selection" | "whole") {
    if (!catchment) return;
    setCombining(`${scope}-report`);
    try {
      const blob = await reportExport(catchment.id, {
        scope,
        areaCodes: scope === "selection" ? Array.from(starred) : undefined,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "landlynk-report.pptx";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      setStatus("Could not build the report deck.");
    } finally {
      setCombining(null);
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

  // Once a run completes, collapse the form so the run title and results lead.
  useEffect(() => {
    if (catchment?.status === "complete") setShowForm(false);
  }, [catchment?.id, catchment?.status]);

  // On Find a site, overlay the brownfield development sites in the catchment.
  useEffect(() => {
    if (intent === "find_site" && catchment?.status === "complete") {
      getCatchmentSites(catchment.id)
        .then(setSites)
        .catch(() => setSites([]));
    } else {
      setSites([]);
    }
  }, [intent, catchment?.id, catchment?.status]);

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
      if (segment) config.segment = segment;
      if (objective) config.objective = objective;
      if (useLookalike && brandLocations.length)
        config.lookalikeLocations = brandLocations;
      if (brandHeading) config.brandHeading = brandHeading;
      if (brandTheme.secondary) config.brandSecondary = brandTheme.secondary;
      if (brandTheme.accent) config.brandAccent = brandTheme.accent;
      if (brandTheme.logoPath) config.brandLogoPath = brandTheme.logoPath;
      if (catchmentMode === "radius") {
        config.catchmentMode = "radius";
        if (radiusKm) config.radiusKm = Number(radiusKm);
      } else {
        config.catchmentMode = "drive_time";
        if (driveTime) config.driveTimeMinutes = Number(driveTime);
      }
      if (affordability) config.affordabilityMultiple = Number(affordability);
      config.overlapThreshold = Number(overlap);
      const weightEntries = Object.entries(weights).map(([k, v]) => [
        k,
        Number(v),
      ]) as [string, number][];
      const weightMap = Object.fromEntries(weightEntries);
      // Find a site can weight the ranking toward brownfield land supply.
      if (intent === "find_site" && weightByLand) weightMap.land_supply = 0.2;
      config.weights = weightMap;

      // Find-a-site has no named scheme yet, so label the run by its audience.
      const developmentNameToSend =
        intent === "find_site" && !developmentName
          ? `${audienceLabel ?? "Audience"} search`
          : developmentName;
      const { id } = await submitCatchment({
        kind,
        value,
        developmentName: developmentNameToSend,
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
            New catchment
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

      {activeRun && !showForm && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-card border border-neutral-200 bg-white px-4 py-3">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-neutral-400">
              Current catchment
            </p>
            <h2 className="truncate text-lg font-semibold tracking-tight">
              {runTitle}
            </h2>
          </div>
          <button
            type="button"
            onClick={() => setShowForm(true)}
            className="shrink-0 rounded-card bg-light-accent px-4 py-2 text-sm font-semibold text-white transition hover:brightness-95"
          >
            New catchment
          </button>
        </div>
      )}

      {showForm && !activeBrand?.industry && (
        <div className="rounded-card border border-neutral-200 bg-white p-4">
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium text-neutral-500">
              Sector
            </span>
            <select
              value={pickedIndustry}
              onChange={(e) => setPickedIndustry(e.target.value)}
              className="w-full rounded-card border border-neutral-300 bg-white px-3 py-2 text-sm focus:border-light-accent focus:outline-none"
            >
              <option value="">Choose a sector</option>
              {INDUSTRIES.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.label}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-neutral-400">
              Tailors the audience segments, and for housebuilding the Find,
              Appraise and Next-phase options.
            </p>
          </label>
        </div>
      )}

      {showForm && isHousebuilder && (
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-neutral-400">
            What do you want to do?
          </p>
          <IntentCards value={intent} onChange={chooseIntent} />
        </div>
      )}

      {showForm && (
      <form
        onSubmit={onSubmit}
        className="space-y-5 rounded-card border border-neutral-200 bg-white p-5 sm:p-6"
      >
        {intent === "find_site" && (
          <div>
            <span className="mb-1.5 block text-xs font-medium text-neutral-500">
              Target audience
            </span>
            <select
              value={segment}
              onChange={(e) => setSegment(e.target.value)}
              className="w-full rounded-card border border-neutral-300 bg-white px-3 py-2 text-sm focus:border-light-accent focus:outline-none"
            >
              <option value="">Choose the buyer you are building for</option>
              {segmentOptions.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.label} — {s.description}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-neutral-400">
              We rank the areas in the search around the location below that best
              fit this buyer.
            </p>
            <label className="mt-2 flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                checked={weightByLand}
                onChange={(e) => setWeightByLand(e.target.checked)}
                className="mt-0.5"
              />
              <span>
                Weight toward areas with more buildable land
                <span className="text-neutral-400">
                  {" "}
                  (brownfield register capacity; load the Development sites data)
                </span>
              </span>
            </label>
          </div>
        )}

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
            label={
              intent === "find_site"
                ? "Search label (optional)"
                : "Site name (optional)"
            }
            value={developmentName}
            onChange={setDevelopmentName}
            placeholder={
              intent === "find_site"
                ? "e.g. Downsizer search"
                : "e.g. Land off Mill Road"
            }
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
              {profiles.length > 0 && (
                <div>
                  <span className="mb-1.5 block text-xs font-medium text-neutral-500">
                    Builder profile
                  </span>
                  <select
                    value={profileId}
                    onChange={(e) => applyProfile(e.target.value)}
                    className="w-full rounded-card border border-neutral-300 bg-white px-3 py-2 text-sm focus:border-light-accent focus:outline-none"
                  >
                    <option value="">None (manual brief)</option>
                    {profiles.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.groupName ? `${p.groupName} · ` : ""}
                        {p.builderName ? `${p.builderName} · ` : ""}
                        {p.name}
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 text-xs text-neutral-400">
                    Fills the brief and themes exports with the brand colour.
                  </p>
                </div>
              )}
              {profiles.length === 0 && isAdmin && (
                <p className="text-xs text-neutral-400">
                  No brand profiles yet.{" "}
                  <a href="/builders" className="text-light-accent underline">
                    Create one in Brands
                  </a>{" "}
                  to fill the brief and theme exports in one click.
                </p>
              )}
              <div>
                <span className="mb-1.5 block text-xs font-medium text-neutral-500">
                  Objective / business focus
                </span>
                <select
                  value={objective}
                  onChange={(e) => applyObjective(e.target.value)}
                  className="w-full rounded-card border border-neutral-300 bg-white px-3 py-2 text-sm focus:border-light-accent focus:outline-none"
                >
                  <option value="">Home sales (default)</option>
                  {OBJECTIVES.filter((o) => o.id !== "home_sales").map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.label} — {o.description}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-neutral-400">
                  Reweights scoring and frames the AI commentary to what you are
                  using the catchment for. Adjust the weights below to fine tune.
                </p>
              </div>
              {brandLocations.length > 0 && (
                <label className="flex items-start gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={useLookalike}
                    onChange={(e) => toggleLookalike(e.target.checked)}
                    className="mt-0.5"
                  />
                  <span>
                    Weight toward areas similar to this brand&apos;s best
                    locations
                    <span className="text-neutral-400">
                      {" "}
                      ({brandLocations.length} location
                      {brandLocations.length === 1 ? "" : "s"})
                    </span>
                  </span>
                </label>
              )}
              <div>
                <span className="mb-1.5 block text-xs font-medium text-neutral-500">
                  Target segment
                </span>
                <select
                  value={segment}
                  onChange={(e) => setSegment(e.target.value)}
                  className="w-full rounded-card border border-neutral-300 bg-white px-3 py-2 text-sm focus:border-light-accent focus:outline-none"
                >
                  <option value="">Balanced (no segment)</option>
                  {segmentOptions.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.label} — {s.description}
                    </option>
                  ))}
                </select>
                <p className="mt-1 text-xs text-neutral-400">
                  Ranks the catchment for this audience. Leave balanced to use the
                  default preferences.
                </p>
              </div>
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
                <div>
                  <span className="mb-1.5 block text-xs font-medium text-neutral-500">
                    Catchment
                  </span>
                  <Segmented
                    options={[
                      { value: "driveTime", label: "Drive time" },
                      { value: "radius", label: "Radius" },
                    ]}
                    value={catchmentMode}
                    onChange={(v) =>
                      setCatchmentMode(v as "driveTime" | "radius")
                    }
                  />
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                {catchmentMode === "driveTime" ? (
                  <Field
                    label="Drive time"
                    suffix="min"
                    hint="roughly how far buyers move for a new home"
                    value={driveTime}
                    onChange={setDriveTime}
                    placeholder="30"
                    type="number"
                  />
                ) : (
                  <Field
                    label="Radius"
                    suffix="km"
                    hint="straight-line, good for cities"
                    value={radiusKm}
                    onChange={setRadiusKm}
                    placeholder="1.5"
                    type="number"
                  />
                )}
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
                      {Object.keys(weights).map((key) => (
                        <Field
                          key={key}
                          label={SIGNAL_LABELS[key] ?? key}
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
            disabled={busy || !canSubmit}
            className="w-full rounded-card bg-light-accent px-5 py-2.5 text-sm font-semibold text-white transition hover:brightness-95 disabled:opacity-50 sm:w-auto"
          >
            {busy
              ? intent === "find_site"
                ? "Finding areas..."
                : "Building..."
              : intent === "find_site"
                ? "Find areas"
                : "Build catchment"}
          </button>
          {status && <p className="text-xs text-neutral-500">{status}</p>}
        </div>
      </form>
      )}

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

      {activeRun && isHousebuilder && intent === "appraise" && (
        <VerdictPanel catchmentId={catchment!.id} />
      )}

      {activeRun && isHousebuilder && intent === "next_phase" && (
        <MixPanel catchmentId={catchment!.id} />
      )}

      {catchment?.status === "complete" && areas.length > 0 && (
        <AreaProfilePanel
          catchmentId={catchment.id}
          starred={Array.from(starred)}
        />
      )}

      {catchment?.status === "complete" && areas.length > 0 && (
        <div className="space-y-3 rounded-card border border-neutral-200 bg-white p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium text-neutral-500">
                Filter
              </span>
              {/* On Find a site the audience is already the lens, so the
                  audience filter pills are redundant; keep just the ranges. */}
              {intent !== "find_site" &&
                SIGNAL_TAGS.map((t) => {
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
                    title="One slide per starred area"
                    className="flex items-center gap-2 rounded-card bg-light-accent px-3 py-2 text-sm font-semibold text-white transition hover:brightness-95 disabled:opacity-50"
                  >
                    <Download size={16} />
                    {exporting === "pdf" ? "..." : "Deck PDF"}
                  </button>
                  <button
                    type="button"
                    onClick={() => exportShortlist("pptx")}
                    disabled={exporting !== null}
                    title="One slide per starred area"
                    className="flex items-center gap-2 rounded-card border border-light-accent px-3 py-2 text-sm font-semibold text-light-accent transition hover:bg-light-accent/5 disabled:opacity-50"
                  >
                    <Download size={16} />
                    {exporting === "pptx" ? "..." : "Deck PPTX"}
                  </button>
                  <button
                    type="button"
                    onClick={() => exportCombined("pdf", "selection")}
                    disabled={combining !== null}
                    title="Merge starred areas into one Battlecard"
                    className="flex items-center gap-2 rounded-card border border-neutral-300 px-3 py-2 text-sm font-semibold disabled:opacity-50"
                  >
                    <Download size={16} />
                    {combining === "selection-pdf" ? "..." : "Combine PDF"}
                  </button>
                  <button
                    type="button"
                    onClick={() => exportCombined("pptx", "selection")}
                    disabled={combining !== null}
                    title="Merge starred areas into one Battlecard"
                    className="flex items-center gap-2 rounded-card border border-neutral-300 px-3 py-2 text-sm font-semibold disabled:opacity-50"
                  >
                    <Download size={16} />
                    {combining === "selection-pptx" ? "..." : "Combine PPTX"}
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
              <button
                type="button"
                onClick={() => exportCombined("pptx", "whole")}
                disabled={combining !== null}
                title="One Battlecard aggregating the whole catchment"
                className="flex items-center gap-2 rounded-card border border-neutral-300 px-3 py-2 text-sm font-semibold disabled:opacity-50"
              >
                <Download size={16} />
                {combining === "whole-pptx" ? "..." : "Whole catchment"}
              </button>
              <button
                type="button"
                onClick={() => exportReport("whole")}
                disabled={combining !== null}
                title="Full multi-slide report deck for the whole catchment"
                className="flex items-center gap-2 rounded-card bg-light-accent px-3 py-2 text-sm font-semibold text-white transition hover:brightness-95 disabled:opacity-50"
              >
                <Download size={16} />
                {combining === "whole-report" ? "..." : "Full report"}
              </button>
              <a
                href={`/api/catchments/${catchment.id}/kml`}
                className="flex items-center gap-2 rounded-card border border-neutral-300 px-3 py-2 text-sm font-semibold"
              >
                <Download size={16} /> KML
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

      <div className="space-y-4">
        <CatchmentMap
          areas={areas}
          isochrone={catchment?.isochrone ?? null}
          coordinate={catchment?.coordinate ?? null}
          onSelectArea={onSelectArea}
          selectedAreaCode={selectedCode}
          matchedCodes={matchedCodes}
          tagContext={tagContext}
          sites={intent === "find_site" ? sites : undefined}
        />
        {activeRun && intent === "find_site" && (
          <p className="text-xs text-neutral-500">
            {sites.length > 0
              ? `${sites.length} brownfield development site${sites.length === 1 ? "" : "s"} in this catchment (green markers), from the national land register.`
              : "No brownfield register sites loaded for this catchment. An admin can load the Development sites dataset on the Reference data page."}
          </p>
        )}
        {activeRun &&
          (() => {
            const cfg = catchment?.input?.config;
            const desc =
              cfg?.catchmentMode === "radius" && cfg?.radiusKm
                ? `a ${cfg.radiusKm} km radius around the location`
                : `a ${cfg?.driveTimeMinutes ?? 30}-minute drive time, roughly how far buyers move for a new home in their area`;
            return (
              <p className="text-xs text-neutral-500">
                The shaded zone is the catchment: {desc}. Areas inside it are
                where buyers are most likely to come from, scored and ranked
                below.
              </p>
            );
          })()}
        <div className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-sm font-semibold text-neutral-500">
              Priority ranking
              {activeFilterCount > 0 && (
                <span className="ml-1 font-normal text-neutral-400">
                  ({filteredAreas.length} of {areas.length})
                </span>
              )}
            </h2>
            {intent === "find_site" && areas.length > 0 && (
              <Segmented
                options={[
                  { value: "fit", label: "Best fit" },
                  { value: "land", label: "Most land" },
                ]}
                value={rankSort}
                onChange={(v) => setRankSort(v as "fit" | "land")}
              />
            )}
          </div>
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
              areas={rankedAreas}
              onSelectArea={onSelectArea}
              selectedAreaCode={selectedCode}
              starredCodes={starred}
              onToggleStar={toggleStar}
              tagContext={tagContext}
              plotsByArea={intent === "find_site" ? plotsByArea : undefined}
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
        priceSet={runPriceSet}
        audienceLabel={runAudienceLabel}
        sites={
          intent === "find_site"
            ? sites.filter((s) => s.areaCode === selectedCode)
            : undefined
        }
        catchmentHasSites={sites.length > 0}
        audienceSegment={runConfig?.segment}
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
