"use client";

import { useCallback, useEffect, useState } from "react";
import { Database, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import {
  getReferenceStatus,
  loadReference,
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
  fields: FieldDef[];
}

const DATASETS: DatasetDef[] = [
  {
    id: "geo_boundaries",
    title: "Area boundaries",
    essential: true,
    blurb:
      "Required for areas to appear. From the ONS Open Geography Portal ArcGIS service (the layer's /query URL). The default is MSOA December 2021 (BGC); for LA level, select LA above and paste the LAD boundaries query URL.",
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
    fields: [
      {
        key: "url",
        label: "HPSSA XLSX or CSV URL",
        placeholder: "ONS median house prices xlsx, or the dataset page URL",
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
  });
  const [areaType, setAreaType] = useState<"MSOA" | "LA">("MSOA");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const refresh = useCallback(() => {
    getReferenceStatus()
      .then(setStatus)
      .catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 4000);
    return () => clearInterval(id);
  }, [refresh]);

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

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => onLoad(d)}
                disabled={s?.status === "running"}
                className="rounded-card bg-light-accent px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
              >
                {s?.status === "running" ? "Loading..." : "Load"}
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
