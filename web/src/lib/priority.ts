import type { PriorityBand } from "./types/battlecard";

// Priority colours must pass contrast and not rely on colour alone. Pair colour
// with rank number and label (design-framework.md, accessibility). These map the
// semantic bands to their tokens and human labels.

export const PRIORITY_COLORS: Record<PriorityBand, string> = {
  high: "#34C759",
  mid: "#FF9500",
  low: "#FF3B30",
};

export const PRIORITY_LABELS: Record<PriorityBand, string> = {
  high: "High priority",
  mid: "Mid priority",
  low: "Low priority",
};

/** Derive a band from a 0 to 1 score using the default thresholds. */
export function bandForScore(score: number): PriorityBand {
  if (score >= 0.66) return "high";
  if (score >= 0.33) return "mid";
  return "low";
}
