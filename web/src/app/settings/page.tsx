"use client";

import { useEffect, useState } from "react";
import { useSession, signOut } from "next-auth/react";
import { Settings, LogOut, Check } from "lucide-react";
import {
  DEFAULT_SETTINGS,
  loadSettings,
  saveSettings,
  type AppSettings,
} from "@/lib/settings";

// Settings: the signed-in account, and the editable default assumptions the
// catchment form starts from (affordability multiple, overlap threshold and
// scoring weights). Defaults are stored in the browser; the values actually
// used are saved with each catchment by the worker, so any ranking stays
// reproducible regardless of later changes here.

const WEIGHT_LABELS: [keyof AppSettings["weights"], string][] = [
  ["income_fit", "Income fit"],
  ["tenure_signal", "Tenure signal"],
  ["age_skew", "Age skew"],
  ["addressable_scale", "Addressable scale"],
  ["household_type", "Household type"],
];

export default function SettingsPage() {
  const { data: session } = useSession();
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setSettings(loadSettings());
  }, []);

  const update = (patch: Partial<AppSettings>) => {
    setSettings((s) => ({ ...s, ...patch }));
    setSaved(false);
  };
  const updateWeight = (key: keyof AppSettings["weights"], value: number) => {
    setSettings((s) => ({ ...s, weights: { ...s.weights, [key]: value } }));
    setSaved(false);
  };

  const onSave = () => {
    saveSettings(settings);
    setSaved(true);
  };
  const onReset = () => {
    setSettings(DEFAULT_SETTINGS);
    saveSettings(DEFAULT_SETTINGS);
    setSaved(true);
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-4">
      <h1 className="flex items-center gap-2 text-lg font-semibold">
        <Settings size={20} /> Settings
      </h1>

      <section className="rounded-card border border-neutral-200 bg-white p-5">
        <h2 className="mb-2 text-sm font-semibold">Account</h2>
        <p className="text-sm text-neutral-500">
          {session?.user?.name ?? session?.user?.email ?? "Signed in"}
        </p>
        <button
          type="button"
          onClick={() => signOut({ callbackUrl: "/signin" })}
          className="mt-3 flex items-center gap-2 rounded-card border border-neutral-300 px-3 py-2 text-sm font-semibold"
        >
          <LogOut size={16} /> Sign out
        </button>
      </section>

      <section className="space-y-5 rounded-card border border-neutral-200 bg-white p-5">
        <div>
          <h2 className="text-sm font-semibold">Default assumptions</h2>
          <p className="mt-1 text-xs text-neutral-500">
            These seed the catchment form. The values used are stored with each
            run, so changing them here never alters a past ranking. A run built
            on different assumptions is flagged on its results.
          </p>
        </div>

        <label className="flex items-start justify-between gap-4 rounded-card border border-neutral-200 px-3 py-3">
          <span>
            <span className="block text-sm font-medium">
              Local Authority (LA) area level
            </span>
            <span className="mt-0.5 block text-xs text-neutral-500">
              MSOA is the default and recommended level. Turn this on to also
              offer LA-level catchments in the form. Note income data is
              MSOA-only, so LA income is not yet available.
            </span>
          </span>
          <input
            type="checkbox"
            checked={settings.enableLA}
            onChange={(e) => update({ enableLA: e.target.checked })}
            className="mt-1 h-5 w-5 shrink-0 accent-light-accent"
          />
        </label>

        <div className="grid gap-4 sm:grid-cols-2">
          <NumberField
            label="Affordability multiple"
            hint="× gross household income"
            value={settings.affordabilityMultiple}
            step={0.1}
            onChange={(v) => update({ affordabilityMultiple: v })}
          />
          <NumberField
            label="Overlap threshold"
            hint="0 to 1"
            value={settings.overlapThreshold}
            step={0.05}
            onChange={(v) => update({ overlapThreshold: v })}
          />
        </div>

        <div>
          <p className="mb-2 text-xs font-medium text-neutral-500">
            Scoring weights
            <span className="ml-1 font-normal text-neutral-400">
              normalised, need not sum to 1
            </span>
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            {WEIGHT_LABELS.map(([key, label]) => (
              <NumberField
                key={key}
                label={label}
                value={settings.weights[key]}
                step={0.05}
                onChange={(v) => updateWeight(key, v)}
              />
            ))}
          </div>
        </div>

        <div className="flex items-center gap-3 border-t border-neutral-200 pt-4">
          <button
            type="button"
            onClick={onSave}
            className="flex items-center gap-2 rounded-card bg-light-accent px-4 py-2 text-sm font-semibold text-white transition hover:brightness-95"
          >
            {saved ? <Check size={16} /> : null}
            {saved ? "Saved" : "Save defaults"}
          </button>
          <button
            type="button"
            onClick={onReset}
            className="text-xs font-medium text-neutral-400 hover:text-neutral-700"
          >
            Reset to defaults
          </button>
        </div>
      </section>
    </div>
  );
}

function NumberField({
  label,
  hint,
  value,
  step,
  onChange,
}: {
  label: string;
  hint?: string;
  value: number;
  step: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-neutral-500">
        {label}
        {hint && (
          <span className="ml-1 font-normal text-neutral-400">{hint}</span>
        )}
      </span>
      <input
        type="number"
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full rounded-card border border-neutral-300 bg-white px-3 py-2.5 text-sm outline-none transition focus:border-light-accent focus:ring-2 focus:ring-light-accent/20"
      />
    </label>
  );
}
