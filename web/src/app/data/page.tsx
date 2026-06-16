"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Database,
  Loader2,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Upload,
} from "lucide-react";
import {
  getReferenceStatus,
  getReferenceHealth,
  loadReference,
  uploadReference,
  type ReferenceStatus,
} from "@/lib/client";
import { useUser } from "@/lib/userContext";

// Reference data is loaded server-side: the worker downloads the open ONS data
// and loads PostGIS. No local commands. Paste each source URL (boundaries is
// pre-filled) and press Load.

const DEFAULT_BOUNDARIES =
  "https://services1.arcgis.com/ESMARspQHYMw9BZ9/arcgis/rest/services/" +
  "Middle_layer_Super_Output_Areas_December_2021_Boundaries_EW_BGC_V3/FeatureServer/0/query";

// NOMIS bulk census 2021 downloads: a zip per table containing one CSV per
// geography. The worker picks the right geography CSV automatically.
const NOMIS = "https://www.nomisweb.co.uk/output/census/2021/census2021-";
const DEFAULT_AGE = `${NOMIS}ts007.zip`;
const DEFAULT_HOUSEHOLDS = `${NOMIS}ts003.zip`;
const DEFAULT_TENURE = `${NOMIS}ts054.zip`;

// ONS Median house prices by MSOA, latest edition (year ending Sep 2025). For a
// newer edition, paste either the new xlsx link or the dataset page itself: the
// loader follows an ONS dataset page to its download automatically.
const DEFAULT_HOUSE_PRICES =
  "https://www.ons.gov.uk/file?uri=/peoplepopulationandcommunity/" +
  "housing/datasets/medianhousepricesbymiddlelayersuperoutputarea/" +
  "yearendingseptember2025/medianpricepaidmsoa.xlsx";

// ONS small-area income (MSOA, financial year ending 2020). Best-known URL;
// update here if ONS publishes a newer release.
const DEFAULT_INCOME =
  "https://www.ons.gov.uk/file?uri=/employmentandlabourmarket/peopleinwork/" +
  "earningsandworkinghours/datasets/" +
  "smallareaincomeestimatesformiddlelayersuperoutputareasenglandandwales/" +
  "financialyearending2020/saiefy1920finalqaddownload280923.xlsx";

// ONS public green space reference tables (April 2020). Published at LSOA with
// an MSOA code on each row; the loader averages distance to MSOA. This is the
// public green space file, not the private outdoor space (gardens) one.
const DEFAULT_GREEN_SPACE =
  "https://www.ons.gov.uk/file?uri=/economy/environmentalaccounts/datasets/" +
  "accesstogardensandpublicgreenspaceingreatbritain/" +
  "accesstopublicparksandplayingfieldsgreatbritainapril2020/" +
  "ospublicgreenspacereferencetables.xlsx";

// MHCLG English Indices of Deprivation 2019, File 7 (all scores, ranks, deciles)
// at LSOA. Aggregated to MSOA with the lookup below.
const DEFAULT_IMD =
  "https://assets.publishing.service.gov.uk/government/uploads/system/uploads/" +
  "attachment_data/file/845345/" +
  "File_7_-_All_IoD2019_Scores__Ranks__Deciles_and_Population_Denominators_3.csv";

// GIAS publishes a new full extract every day with the date in the filename, so
// default to today's URL. The worker steps back a day at a time if today's file
// is not up yet, so this just works without hunting for the dated link.
const _today = new Date().toISOString().slice(0, 10).replace(/-/g, "");
const DEFAULT_SCHOOLS =
  "https://ea-edubase-api-prod.azurewebsites.net/edubase/downloads/public/" +
  `edubasealldata${_today}.csv`;

// NHS ODS Organisation Reference Data API. The list endpoint pages by
// Offset/Limit and returns each organisation's ODS code, name and postcode;
// the worker geocodes the postcode against the Postcodes dataset. RO198 is the
// NHS Trust Site role; change PrimaryRoleId for a different set.
const DEFAULT_HOSPITALS =
  "https://directory.spineservices.nhs.uk/ORD/2-0-0/organisations?" +
  "PrimaryRoleId=RO198&Limit=1000";

interface FieldDef {
  key: string;
  label: string;
  placeholder: string;
}

interface DatasetDef {
  id: string;
  title: string;
  essential?: boolean;
  blurb: string;
  // Official page to get the data from, for the ones that are not auto-loaded.
  source?: string;
  sourceLabel?: string;
  // Sources with no stable URL (e.g. data.police.uk custom downloads): the admin
  // builds and downloads the file, then uploads it here.
  upload?: boolean;
  fields: FieldDef[];
}

const DATASETS: DatasetDef[] = [
  {
    id: "geo_boundaries",
    title: "Area boundaries",
    essential: true,
    blurb:
      "Required for areas to appear. From the ONS Open Geography Portal ArcGIS service (the layer's /query URL). The default is MSOA December 2021 (BGC); for LA level, select LA above and paste the LAD boundaries query URL.",
    source: "https://geoportal.statistics.gov.uk/",
    sourceLabel: "ONS Open Geography Portal",
    fields: [
      {
        key: "url",
        label: "ArcGIS query URL",
        placeholder: DEFAULT_BOUNDARIES,
      },
    ],
  },
  {
    id: "census_demographics",
    title: "Census demographics (age and households)",
    blurb:
      "Population, age bands, median age and family household share. Two NOMIS bulk CSVs: age by single year (TS007) and household composition (TS003).",
    source: "https://www.nomisweb.co.uk/sources/census_2021_bulk",
    sourceLabel: "NOMIS Census 2021 bulk",
    fields: [
      {
        key: "ageUrl",
        label: "Age CSV URL (TS007)",
        placeholder: "https://www.nomisweb.co.uk/...",
      },
      {
        key: "householdsUrl",
        label: "Household composition CSV URL (TS003)",
        placeholder: "https://www.nomisweb.co.uk/...",
      },
    ],
  },
  {
    id: "census_tenure",
    title: "Census tenure",
    blurb:
      "Owns outright, owns with mortgage, social and private rented. NOMIS bulk CSV (TS054).",
    source: "https://www.nomisweb.co.uk/sources/census_2021_bulk",
    sourceLabel: "NOMIS Census 2021 bulk",
    fields: [
      {
        key: "url",
        label: "Tenure CSV URL (TS054)",
        placeholder: "https://www.nomisweb.co.uk/...",
      },
    ],
  },
  {
    id: "income_estimates",
    title: "Income estimates",
    blurb:
      "Mean and median net annual household income by MSOA. ONS small-area income spreadsheet (XLSX) or a CSV.",
    source:
      "https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/" +
      "earningsandworkinghours/datasets/" +
      "smallareaincomeestimatesformiddlelayersuperoutputareasenglandandwales",
    sourceLabel: "ONS small area income",
    fields: [
      {
        key: "url",
        label: "Income XLSX or CSV URL",
        placeholder: "https://www.ons.gov.uk/...xlsx",
      },
    ],
  },
  {
    id: "house_prices",
    title: "House prices",
    blurb:
      "Local median house price by MSOA, for site appraisal and scheme pricing. ONS House Price Statistics for Small Areas (HPSSA), median price paid (XLSX).",
    source:
      "https://www.ons.gov.uk/peoplepopulationandcommunity/housing/datasets/" +
      "medianhousepricesbymiddlelayersuperoutputarea",
    sourceLabel: "ONS HPSSA median price",
    fields: [
      {
        key: "url",
        label: "HPSSA XLSX or CSV URL",
        placeholder: "ONS median house prices xlsx, or the dataset page URL",
      },
    ],
  },
  {
    id: "green_space",
    title: "Green space",
    blurb:
      "Walk time to the nearest green space by MSOA, shown as local context. Use the ONS public green space reference tables (the 'OS public green space' xlsx, not the private outdoor space one). It is published at LSOA; the loader averages to MSOA. Easiest to download the xlsx and upload it below.",
    source:
      "https://www.ons.gov.uk/economy/environmentalaccounts/datasets/" +
      "accesstogardensandpublicgreenspaceingreatbritain",
    sourceLabel: "ONS public green space",
    upload: true,
    fields: [
      {
        key: "url",
        label: "Green space XLSX or CSV URL",
        placeholder: "ONS green space xlsx, or the dataset page URL",
      },
    ],
  },
  {
    id: "imd",
    title: "Deprivation (IMD)",
    blurb:
      "Index of Multiple Deprivation, aggregated from LSOA to MSOA, as local context. The IMD file (File 7) is pre-filled. Leave the lookup blank to use the LSOA-to-MSOA lookup built from the Postcodes dataset (load Postcodes first), or paste an LSOA-to-MSOA lookup CSV to override.",
    source: "https://www.gov.uk/government/statistics/english-indices-of-deprivation-2019",
    sourceLabel: "MHCLG IoD2019",
    fields: [
      {
        key: "url",
        label: "IMD (LSOA) CSV or XLSX URL",
        placeholder: "MHCLG IMD LSOA file",
      },
      {
        key: "lookupUrl",
        label: "LSOA to MSOA lookup CSV URL",
        placeholder: "ONS Open Geography: LSOA(2011) to MSOA(2011) lookup, CSV export",
      },
    ],
  },
  {
    id: "schools",
    title: "Schools (Ofsted)",
    blurb:
      "Count of schools per MSOA from the GIAS extract (its date-stamped daily file auto-loads). GIAS carries the location but not the Ofsted rating, so add the optional Ofsted outcomes file (keyed by URN) to also get the share rated Good or Outstanding.",
    source: "https://get-information-schools.service.gov.uk/Downloads",
    sourceLabel: "GIAS downloads",
    fields: [
      {
        key: "url",
        label: "GIAS edubasealldata CSV URL",
        placeholder: "get-information-schools.service.gov.uk/Downloads, edubasealldata CSV",
      },
      {
        key: "ratingsUrl",
        label: "Ofsted outcomes file URL (optional, for Good/Outstanding %)",
        placeholder:
          "Ofsted state-funded schools inspections management information (CSV/XLSX with URN + outcome)",
      },
    ],
  },
  {
    id: "crime",
    title: "Crime",
    blurb:
      "Recorded crime per 1,000 residents per MSOA, as local context. data.police.uk only offers custom-built downloads, so build the period and forces you want, download the archive, then upload it here (a zip of monthly CSVs, or a single CSV).",
    source: "https://data.police.uk/data/",
    sourceLabel: "data.police.uk (build your download)",
    upload: true,
    fields: [
      {
        key: "url",
        label: "Or paste a CSV or zip URL (optional)",
        placeholder: "data.police.uk/data: build a CSV/zip, or upload the file below",
      },
    ],
  },
  {
    id: "postcodes",
    title: "Postcodes (geocoding)",
    blurb:
      "ONS Postcode Directory: maps every postcode to a coordinate. Used to geocode NHS hospital postcodes from the ODS API, so load this before Hospitals. Paste the current ONSPD zip link from the ONS Geography Portal.",
    source: "https://geoportal.statistics.gov.uk/search?q=ONS%20Postcode%20Directory",
    sourceLabel: "ONS Postcode Directory",
    fields: [
      {
        key: "url",
        label: "ONSPD / NSPL zip URL",
        placeholder: "ONS Geography Portal: ONS Postcode Directory full zip",
      },
    ],
  },
  {
    id: "hospitals",
    title: "Hospitals",
    blurb:
      "Distance to the nearest hospital per MSOA, plus the points used for the nearest-A&E context on reports. Loads live from the NHS ODS organisation API (org code plus postcode), geocoded against the Postcodes dataset, so load Postcodes first. The default lists NHS Trust sites; adjust PrimaryRoleId for a different ODS role. A plain hospital-sites CSV with lat/long or easting/northing also works.",
    source:
      "https://digital.nhs.uk/developer/api-catalogue/organisation-data-service-ord",
    sourceLabel: "NHS ODS ORD API",
    fields: [
      {
        key: "url",
        label: "ODS ORD API URL (or a hospital-sites CSV URL)",
        placeholder: "NHS ODS organisations API endpoint, or an NHS sites CSV",
      },
    ],
  },
  {
    id: "development_sites",
    title: "Development sites (brownfield)",
    blurb:
      "Buildable sites from the national brownfield land register, shown within a catchment on the Find a site flow, with dwelling capacity. Paste the planning.data.gov.uk brownfield-land dataset CSV (it carries a point column with hectares and net dwellings). Open Government Licence.",
    source: "https://www.planning.data.gov.uk/dataset/brownfield-land",
    sourceLabel: "planning.data.gov.uk brownfield land",
    fields: [
      {
        key: "url",
        label: "Brownfield land CSV URL",
        placeholder: "planning.data.gov.uk brownfield-land CSV download",
      },
    ],
  },
  {
    id: "site_allocations",
    title: "Local Plan allocations",
    blurb:
      "Sites allocated for housing in adopted Local Plans, including greenfield land the brownfield register misses. Shown as buildable land alongside brownfield on Find a site. Paste a planning.data.gov.uk allocation CSV with a point column and net dwellings.",
    source: "https://www.planning.data.gov.uk/",
    sourceLabel: "planning.data.gov.uk",
    fields: [
      {
        key: "url",
        label: "Allocations CSV URL",
        placeholder: "planning.data.gov.uk allocation CSV with point and dwellings",
      },
    ],
  },
  {
    id: "planning_permissions",
    title: "Competitor developments",
    blurb:
      "Residential planning permissions, shown as a toggleable competitor-developments overlay on Find a site (where rivals are already building), not counted as your buildable land. Paste a CSV with a point column (or lat/long) and net dwellings.",
    source: "https://www.planning.data.gov.uk/",
    sourceLabel: "planning.data.gov.uk",
    fields: [
      {
        key: "url",
        label: "Permissions CSV URL",
        placeholder: "residential permissions CSV with point and dwellings",
      },
    ],
  },
];

export default function DataPage() {
  const { isAdmin, loading: userLoading } = useUser();
  const [status, setStatus] = useState<Record<string, ReferenceStatus>>({});
  const [values, setValues] = useState<Record<string, Record<string, string>>>({
    geo_boundaries: { url: DEFAULT_BOUNDARIES },
    census_demographics: {
      ageUrl: DEFAULT_AGE,
      householdsUrl: DEFAULT_HOUSEHOLDS,
    },
    census_tenure: { url: DEFAULT_TENURE },
    income_estimates: { url: DEFAULT_INCOME },
    house_prices: { url: DEFAULT_HOUSE_PRICES },
    green_space: { url: DEFAULT_GREEN_SPACE },
    imd: { url: DEFAULT_IMD, lookupUrl: "" },
    schools: { url: DEFAULT_SCHOOLS, ratingsUrl: "" },
    crime: { url: "" },
    postcodes: { url: "" },
    hospitals: { url: DEFAULT_HOSPITALS },
  });
  const [areaType, setAreaType] = useState<"MSOA" | "LA">("MSOA");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [stale, setStale] = useState<string[]>([]);
  const [files, setFiles] = useState<Record<string, File | null>>({});
  const [uploading, setUploading] = useState<Record<string, boolean>>({});
  const [progress, setProgress] = useState<Record<string, number>>({});

  const refresh = useCallback(() => {
    getReferenceStatus()
      .then(setStatus)
      .catch(() => {});
    getReferenceHealth()
      .then((h) => setStale(h.stale ?? []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 4000);
    return () => clearInterval(id);
  }, [refresh]);

  // Persist the entered source URLs so they survive a reload (datasets without a
  // pre-filled default, like Postcodes and Crime, otherwise look empty on return).
  useEffect(() => {
    try {
      const saved = JSON.parse(
        window.localStorage.getItem("landlynk.referenceUrls") || "{}",
      );
      if (saved && typeof saved === "object") {
        setValues((v) => {
          const merged = { ...v };
          for (const [k, val] of Object.entries(saved)) {
            if (val && typeof val === "object") {
              merged[k] = { ...merged[k], ...(val as Record<string, string>) };
            }
          }
          return merged;
        });
      }
    } catch {
      // Ignore unreadable storage; defaults stand.
    }
  }, []);

  useEffect(() => {
    try {
      window.localStorage.setItem(
        "landlynk.referenceUrls",
        JSON.stringify(values),
      );
    } catch {
      // Storage may be unavailable (private mode); persistence is best effort.
    }
  }, [values]);

  const setField = (dataset: string, key: string, val: string) =>
    setValues((v) => ({ ...v, [dataset]: { ...v[dataset], [key]: val } }));

  async function onLoad(d: DatasetDef) {
    setErrors((e) => ({ ...e, [d.id]: "" }));
    try {
      await loadReference(d.id, { areaType, ...(values[d.id] ?? {}) });
      refresh();
    } catch (err) {
      setErrors((e) => ({
        ...e,
        [d.id]: err instanceof Error ? err.message : "Failed",
      }));
    }
  }

  async function onUpload(d: DatasetDef) {
    const file = files[d.id];
    if (!file) return;
    setErrors((e) => ({ ...e, [d.id]: "" }));
    setUploading((u) => ({ ...u, [d.id]: true }));
    setProgress((p) => ({ ...p, [d.id]: 0 }));
    try {
      await uploadReference(d.id, file, { areaType }, (f) =>
        setProgress((p) => ({ ...p, [d.id]: f })),
      );
      refresh();
    } catch (err) {
      setErrors((e) => ({
        ...e,
        [d.id]: err instanceof Error ? err.message : "Upload failed",
      }));
    } finally {
      setUploading((u) => ({ ...u, [d.id]: false }));
    }
  }

  if (userLoading) {
    return <p className="p-4 text-sm text-neutral-500">Loading...</p>;
  }
  if (!isAdmin) {
    return (
      <div className="mx-auto max-w-2xl p-4">
        <p className="rounded-card border border-neutral-200 bg-white p-4 text-sm text-neutral-600">
          This page is for admins only.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-4 py-8">
      <header>
        <h1 className="flex items-center gap-2 text-lg font-semibold">
          <Database size={20} /> Reference data
        </h1>
        <p className="mt-1 text-sm text-neutral-600">
          Load the open ONS data the engine scores against. The worker downloads
          and loads it for you. Start with boundaries so areas appear, then add
          census and income for the full Battlecard numbers.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="text-xs text-neutral-500">Area level</span>
          {(["MSOA", "LA"] as const).map((a) => (
            <button
              key={a}
              type="button"
              onClick={() => setAreaType(a)}
              className={`rounded-card px-3 py-1.5 text-sm font-medium ${
                areaType === a
                  ? "bg-light-accent text-white"
                  : "border border-neutral-300"
              }`}
            >
              {a}
            </button>
          ))}
          <span className="text-xs text-neutral-400">
            Loads apply to {areaType}. For LA, paste LA-level source URLs.
          </span>
        </div>
      </header>

      <StatusSummary status={status} stale={stale} />

      {DATASETS.map((d) => {
        const s = status[d.id];
        return (
          <section
            key={d.id}
            className="space-y-3 rounded-card border border-neutral-200 p-5"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="flex items-center gap-2 text-sm font-semibold">
                  {d.title}
                  {d.essential && (
                    <span className="rounded-full bg-light-accent/10 px-2 py-0.5 text-[11px] font-semibold text-light-accent">
                      essential
                    </span>
                  )}
                </h2>
                <p className="mt-1 text-xs text-neutral-500">{d.blurb}</p>
                {d.source && (
                  <a
                    href={d.source}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-1.5 inline-flex items-center gap-1 text-xs font-medium text-light-accent hover:underline"
                  >
                    <ExternalLink size={12} />
                    Get the data{d.sourceLabel ? `: ${d.sourceLabel}` : ""}
                  </a>
                )}
              </div>
              <StatusBadge status={s} />
            </div>

            {d.fields.map((f) => (
              <label key={f.key} className="block">
                <span className="mb-1 block text-xs text-neutral-500">
                  {f.label}
                </span>
                <input
                  value={values[d.id]?.[f.key] ?? ""}
                  onChange={(e) => setField(d.id, f.key, e.target.value)}
                  placeholder={f.placeholder}
                  className="w-full rounded-card border border-neutral-300 bg-transparent px-3 py-2 text-xs"
                />
              </label>
            ))}

            {d.upload && (
              <div className="rounded-card border border-dashed border-neutral-300 p-3">
                <span className="mb-1.5 block text-xs font-medium text-neutral-600">
                  Upload the downloaded file (CSV, XLSX, or a .zip)
                </span>
                <div className="flex flex-wrap items-center gap-3">
                  <input
                    type="file"
                    accept=".csv,.zip,.xlsx,.xlsm,.xls"
                    onChange={(e) =>
                      setFiles((m) => ({
                        ...m,
                        [d.id]: e.target.files?.[0] ?? null,
                      }))
                    }
                    className="text-xs text-neutral-600 file:mr-3 file:rounded-card file:border-0 file:bg-neutral-100 file:px-3 file:py-1.5 file:text-xs file:font-semibold"
                  />
                  <button
                    type="button"
                    onClick={() => onUpload(d)}
                    disabled={!files[d.id] || uploading[d.id]}
                    className="inline-flex items-center gap-1.5 rounded-card bg-light-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                  >
                    {uploading[d.id] ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <Upload size={14} />
                    )}
                    {uploading[d.id]
                      ? `Uploading ${Math.round((progress[d.id] ?? 0) * 100)}%`
                      : "Upload and load"}
                  </button>
                </div>
                {uploading[d.id] && (
                  <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-neutral-200">
                    <div
                      className="h-full bg-light-accent transition-all"
                      style={{ width: `${Math.round((progress[d.id] ?? 0) * 100)}%` }}
                    />
                  </div>
                )}
                <p className="mt-2 text-xs text-neutral-500">
                  Large files (a national crime archive is over 1GB) upload in
                  the background here. Keep this tab open until it reaches 100%.
                </p>
              </div>
            )}

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => onLoad(d)}
                disabled={s?.status === "running"}
                className="rounded-card bg-light-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
              >
                {s?.status === "running"
                  ? "Loading..."
                  : d.upload
                    ? "Load from URL"
                    : "Load"}
              </button>
              {errors[d.id] && (
                <span className="text-xs text-priority-low">
                  {errors[d.id]}
                </span>
              )}
            </div>
          </section>
        );
      })}
    </div>
  );
}

function StatusBadge({ status }: { status?: ReferenceStatus }) {
  if (!status) {
    return <span className="text-xs text-neutral-400">Not loaded</span>;
  }
  if (status.status === "running") {
    return (
      <span className="flex items-center gap-1 text-xs text-neutral-500">
        <Loader2 size={14} className="animate-spin" /> Loading
      </span>
    );
  }
  if (status.status === "loaded") {
    return (
      <span className="flex items-center gap-1 text-xs text-priority-high">
        <CheckCircle2 size={14} /> {status.rows?.toLocaleString()} rows
      </span>
    );
  }
  if (status.status === "failed") {
    return (
      <span
        className="flex items-center gap-1 text-xs text-priority-low"
        title={status.error ?? ""}
      >
        <AlertCircle size={14} /> Failed
      </span>
    );
  }
  return <span className="text-xs text-neutral-400">{status.status}</span>;
}

// Overview at the top of the page: every dataset with a RAG dot, when it was last
// updated, and any action or error to address. Green = loaded and fresh, amber =
// loading or out of date, red = not loaded or failed.
function StatusSummary({
  status,
  stale,
}: {
  status: Record<string, ReferenceStatus>;
  stale: string[];
}) {
  const staleSet = new Set(stale);

  function rag(id: string): { dot: string; label: string } {
    const s = status[id];
    if (!s || s.status === "not_loaded" || !s.status) {
      return { dot: "bg-priority-low", label: "Not loaded" };
    }
    if (s.status === "failed") return { dot: "bg-priority-low", label: "Failed" };
    if (s.status === "running")
      return { dot: "bg-priority-mid", label: "Loading..." };
    if (staleSet.has(id))
      return { dot: "bg-priority-mid", label: "Out of date, reload" };
    return { dot: "bg-priority-high", label: "Up to date" };
  }

  return (
    <div className="overflow-hidden rounded-card border border-neutral-200 bg-white">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-neutral-200 text-xs text-neutral-500">
          <tr>
            <th className="px-3 py-2 font-semibold">Dataset</th>
            <th className="px-3 py-2 font-semibold">Status</th>
            <th className="px-3 py-2 font-semibold">Last updated</th>
            <th className="px-3 py-2 text-right font-semibold">Rows</th>
            <th className="px-3 py-2 font-semibold">Action / error</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-100">
          {DATASETS.map((d) => {
            const s = status[d.id];
            const { dot, label } = rag(d.id);
            return (
              <tr key={d.id}>
                <td className="px-3 py-2 font-medium">{d.title}</td>
                <td className="px-3 py-2">
                  <span className="flex items-center gap-1.5">
                    <span className={`h-2.5 w-2.5 rounded-full ${dot}`} />
                    <span className="text-xs text-neutral-600">{label}</span>
                  </span>
                </td>
                <td className="whitespace-nowrap px-3 py-2 text-xs text-neutral-500">
                  {s?.updatedAt ? new Date(s.updatedAt).toLocaleDateString() : "-"}
                </td>
                <td className="px-3 py-2 text-right tabular-nums text-xs text-neutral-500">
                  {s?.rows != null ? s.rows.toLocaleString() : "-"}
                </td>
                <td className="px-3 py-2 text-xs text-neutral-500">
                  {s?.status === "failed"
                    ? s.error || "Load failed"
                    : !s || !s.status || s.status === "not_loaded"
                      ? "Load below"
                      : staleSet.has(d.id)
                        ? "Reload for a newer release"
                        : ""}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
