// Business objectives for objective-first targeting. Mirrors the worker registry
// in worker/src/landlynk_worker/scoring/objectives.py; keep ids and weight
// presets in sync. The worker is the source of truth for scoring; these presets
// let the form show and pre-fill the weights when an objective is chosen.

export interface Objective {
  id: string;
  label: string;
  description: string;
  weights: Record<string, number>;
  segment?: string | null;
}

export const OBJECTIVES: Objective[] = [
  {
    id: "home_sales",
    label: "Home sales and marketing",
    description: "Rank areas by fit to a housing scheme's buyers and price.",
    weights: {
      income_fit: 0.3,
      tenure_signal: 0.2,
      age_skew: 0.2,
      addressable_scale: 0.2,
      household_type: 0.1,
    },
  },
  {
    id: "land_acquisition",
    label: "Land acquisition and appraisal",
    description: "Favour demand, scale and sales-value upside for site sourcing.",
    weights: {
      addressable_scale: 0.3,
      income_fit: 0.2,
      income_level: 0.2,
      low_deprivation: 0.15,
      household_type: 0.15,
    },
  },
  {
    id: "wealth_management",
    label: "Wealth management (high net worth)",
    description: "Target the most affluent areas for high net worth lead generation.",
    weights: {
      income_level: 0.4,
      low_deprivation: 0.25,
      low_crime: 0.15,
      green_space: 0.1,
      healthcare_access: 0.1,
    },
    segment: "high_net_worth",
  },
  {
    id: "retail_site",
    label: "Retail and leisure site selection",
    description: "Favour population scale and spend potential for a store or venue.",
    weights: {
      addressable_scale: 0.45,
      income_level: 0.3,
      low_crime: 0.25,
    },
  },
];

// Friendly labels for every scoring signal a weights editor might show.
export const SIGNAL_LABELS: Record<string, string> = {
  income_fit: "Income fit",
  tenure_signal: "Tenure signal",
  age_skew: "Age skew",
  addressable_scale: "Addressable scale",
  household_type: "Household type",
  income_level: "Income level",
  low_deprivation: "Low deprivation",
  green_space: "Green space",
  schools: "Schools",
  low_crime: "Low crime",
  healthcare_access: "Healthcare access",
  lookalike: "Similar to best locations",
};
