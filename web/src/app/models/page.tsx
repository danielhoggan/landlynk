"use client";

import { useEffect, useState } from "react";
import { Sparkles, Check } from "lucide-react";
import { getModels, setDefaultModel, type AiModel } from "@/lib/client";
import { useUser } from "@/lib/userContext";

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: "Anthropic",
  openai: "OpenAI",
  google: "Google",
};

// Admin-only: choose the default AI model for Local Area Profiles. Only models
// whose provider key is set in Railway appear here. Keys are never shown.
export default function ModelsPage() {
  const { isAdmin, loading } = useUser();
  const [models, setModels] = useState<AiModel[] | null>(null);
  const [current, setCurrent] = useState<string | null>(null);
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isAdmin) return;
    getModels()
      .then((r) => {
        setModels(r.models);
        setCurrent(r.default);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, [isAdmin]);

  if (loading) return <p className="p-4 text-sm text-neutral-500">Loading...</p>;
  if (!isAdmin) {
    return (
      <div className="mx-auto max-w-2xl p-4">
        <p className="rounded-card border border-neutral-200 bg-white p-4 text-sm text-neutral-600">
          This page is for admins only.
        </p>
      </div>
    );
  }

  async function choose(id: string) {
    setSaving(id);
    setError("");
    try {
      await setDefaultModel(id);
      setCurrent(id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not set model");
    } finally {
      setSaving(null);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4">
      <h1 className="flex items-center gap-2 text-lg font-semibold">
        <Sparkles size={20} /> AI models
      </h1>
      <p className="text-sm text-neutral-500">
        The default model used for AI Local Area Profiles. Only providers with a
        key configured in Railway appear here. Generated profiles are labelled
        AI-generated and should be reviewed before use.
      </p>

      {error && <p className="text-sm text-priority-low">{error}</p>}
      {models === null && !error && (
        <p className="text-sm text-neutral-500">Loading...</p>
      )}
      {models && models.length === 0 && (
        <p className="rounded-card border border-priority-mid/40 bg-priority-mid/10 p-4 text-sm text-neutral-600">
          No AI providers configured. Add an Anthropic, OpenAI or Google API key
          in Railway to enable Local Area Profiles.
        </p>
      )}

      {models && models.length > 0 && (
        <ul className="divide-y divide-neutral-200 overflow-hidden rounded-card border border-neutral-200 bg-white">
          {models.map((m) => {
            const active = m.id === current;
            return (
              <li
                key={m.id}
                className="flex items-center justify-between gap-3 px-4 py-3"
              >
                <span>
                  <span className="block text-sm font-semibold">{m.label}</span>
                  <span className="block text-xs text-neutral-500">
                    {PROVIDER_LABELS[m.provider] ?? m.provider}
                  </span>
                </span>
                {active ? (
                  <span className="flex items-center gap-1.5 rounded-card bg-light-accent/10 px-3 py-1.5 text-sm font-semibold text-light-accent">
                    <Check size={16} /> Default
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={() => choose(m.id)}
                    disabled={saving !== null}
                    className="rounded-card border border-neutral-300 px-3 py-1.5 text-sm font-semibold transition hover:bg-neutral-100 disabled:opacity-50"
                  >
                    {saving === m.id ? "Setting..." : "Set default"}
                  </button>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
