"use client";

import { Search, ClipboardCheck, Layers, type LucideIcon } from "lucide-react";

// The housebuilder intents that signpost the New catchment page. Each configures
// the same engine differently. "next_phase" is signposted but not built yet.
export type Intent = "find_site" | "appraise" | "next_phase";

const CARDS: {
  id: Intent;
  title: string;
  blurb: string;
  icon: LucideIcon;
  soon?: boolean;
}[] = [
  {
    id: "find_site",
    title: "Find a site",
    blurb: "Rank the areas that best fit a target buyer, to decide where to build.",
    icon: Search,
  },
  {
    id: "appraise",
    title: "Appraise a site",
    blurb: "Evaluate a specific plot: its buyers, pricing and demand depth.",
    icon: ClipboardCheck,
  },
  {
    id: "next_phase",
    title: "Plan the next phase",
    blurb: "Choose the product mix for the rest of a site you already own.",
    icon: Layers,
    soon: true,
  },
];

export function IntentCards({
  value,
  onChange,
}: {
  value: Intent;
  onChange: (intent: Intent) => void;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {CARDS.map((card) => {
        const Icon = card.icon;
        const active = value === card.id;
        return (
          <button
            key={card.id}
            type="button"
            disabled={card.soon}
            aria-pressed={active}
            onClick={() => onChange(card.id)}
            className={`rounded-card border p-4 text-left transition ${
              active
                ? "border-light-accent bg-light-accent/5"
                : "border-neutral-200 hover:border-neutral-300"
            } ${card.soon ? "cursor-not-allowed opacity-60" : ""}`}
          >
            <div className="flex items-center gap-2">
              <Icon
                size={18}
                className={active ? "text-light-accent" : "text-neutral-500"}
              />
              <span className="text-sm font-semibold">{card.title}</span>
              {card.soon && (
                <span className="ml-auto rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-semibold text-neutral-500">
                  Soon
                </span>
              )}
            </div>
            <p className="mt-1.5 text-xs text-neutral-500">{card.blurb}</p>
          </button>
        );
      })}
    </div>
  );
}
