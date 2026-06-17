"use client";

import { ChevronDown } from "lucide-react";

// An on-page accordion explaining how the ranking was built, tailored to the
// housebuilder intent, so a user understands what is shown and why without
// leaving for How it works. Open any area for the exact signal breakdown.
export function RankingExplainer({
  intent,
  audienceLabel,
  affordabilityMultiple,
}: {
  intent: "find_site" | "appraise" | "next_phase";
  audienceLabel?: string | null;
  affordabilityMultiple?: number | null;
}) {
  const audience = audienceLabel ? audienceLabel.toLowerCase() : "the chosen buyer";
  const mult = affordabilityMultiple ?? 4.5;

  const paragraphs: string[] =
    intent === "find_site"
      ? [
          `Areas are scored on how well their residents fit ${audience}: the age profile, the tenure mix and the household types, weighted together with the size of the local market. The list is ordered by that fit, or by buildable land if you switch the sort.`,
          `Suitable shows the stronger-fitting areas in this catchment and hides the weakest third; switch to All areas to see every area. Scores are relative to this catchment, so they compare the areas here rather than against a national bar.`,
          `Green dots are brownfield plots (buildable land with dwelling capacity); red dots are competitor developments (recent residential planning applications nearby). Open any area for the exact signal-by-signal breakdown.`,
        ]
      : intent === "appraise"
        ? [
            `The verdict checks whether local incomes support your price (about ${mult}x household income), how deep demand is by buyer type, and how much buildable land and competing pipeline sit in the catchment.`,
            `Areas are ranked on the land-acquisition signals: demand depth, addressable scale, income and low deprivation. Scores are relative to this catchment. Open any area for the exact signal-by-signal breakdown.`,
          ]
        : [
            `Demand is sized from the catchment's households by buyer type. The recommendation is the deepest pool left once you mark what is already selling slowly, so the final phase leans toward under-served demand.`,
            `Areas are scored on fit and scale, relative to this catchment. Open any area for the exact signal-by-signal breakdown.`,
          ];

  return (
    <details className="group rounded-card border border-neutral-200 bg-white">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 px-4 py-3 text-sm font-semibold">
        How this ranking works
        <ChevronDown
          size={16}
          className="text-neutral-400 transition-transform group-open:rotate-180"
        />
      </summary>
      <div className="space-y-2 px-4 pb-4 text-xs leading-relaxed text-neutral-600">
        {paragraphs.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
        <p className="text-neutral-400">
          Built only on open ONS and planning data, so every ranking is
          reproducible and explainable.
        </p>
      </div>
    </details>
  );
}
