"use client";

import { useSession, signOut } from "next-auth/react";
import { Settings, LogOut } from "lucide-react";

// Settings: the signed-in account, the default scoring weights for reference,
// and sign out. Theme is controlled by the persistent toggle, bottom-left.
const DEFAULT_WEIGHTS: [string, string][] = [
  ["Income fit", "0.30"],
  ["Tenure signal", "0.20"],
  ["Age skew", "0.20"],
  ["Addressable scale", "0.20"],
  ["Household type", "0.10"],
];

export default function SettingsPage() {
  const { data: session } = useSession();

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-4">
      <h1 className="flex items-center gap-2 text-lg font-semibold">
        <Settings size={20} /> Settings
      </h1>

      <section className="rounded-card border border-neutral-200 p-4">
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

      <section className="rounded-card border border-neutral-200 p-4">
        <h2 className="mb-2 text-sm font-semibold">Default scoring weights</h2>
        <p className="mb-3 text-xs text-neutral-500">
          The defaults applied when a catchment does not override them. Tune per
          run from the catchment form; the values are stored with each catchment
          so any ranking stays reproducible.
        </p>
        <dl className="grid grid-cols-2 gap-2">
          {DEFAULT_WEIGHTS.map(([label, value]) => (
            <div
              key={label}
              className="flex items-center justify-between rounded-card border border-neutral-200 px-3 py-2 text-sm"
            >
              <dt className="text-neutral-500">{label}</dt>
              <dd className="font-semibold tabular-nums">{value}</dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}
