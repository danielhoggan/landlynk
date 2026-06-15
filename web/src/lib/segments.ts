// Audience segments for segment-first targeting. Mirrors the worker library in
// worker/src/landlynk_worker/scoring/segments.py; keep the ids in sync. The
// worker is the source of truth for the scoring vectors each segment applies.
// Segments are scoped to an industry; the active brand's industry decides which
// the user sees in the pickers. The full list is kept for display lookups.

export interface Segment {
  id: string;
  industry: string;
  label: string;
  description: string;
  bedRange: string;
}

const NA_BEDS = "2 to 5";

export const SEGMENTS: Segment[] = [
  // residential development / house building
  {
    id: "first_time_buyer",
    industry: "residential",
    label: "First time buyers",
    description: "Young renters stepping onto the ladder.",
    bedRange: "2 to 3",
  },
  {
    id: "second_stepper",
    industry: "residential",
    label: "Second steppers",
    description: "Mortgaged owners trading up.",
    bedRange: "3 to 4",
  },
  {
    id: "growing_family",
    industry: "residential",
    label: "Growing families",
    description: "Mid-life households with children.",
    bedRange: "3 to 5",
  },
  {
    id: "downsizer",
    industry: "residential",
    label: "Downsizers",
    description: "Older outright owners releasing equity.",
    bedRange: "2 to 3",
  },
  {
    id: "high_net_worth",
    industry: "residential",
    label: "High net worth",
    description: "Affluent established owners.",
    bedRange: "4 to 5",
  },
  // retail and hospitality
  {
    id: "urban_professionals",
    industry: "retail",
    label: "Urban professionals",
    description: "Younger working renters and owners with disposable income.",
    bedRange: NA_BEDS,
  },
  {
    id: "family_shoppers",
    industry: "retail",
    label: "Family shoppers",
    description: "Households with children doing the bulk of family spend.",
    bedRange: NA_BEDS,
  },
  {
    id: "affluent_older_shoppers",
    industry: "retail",
    label: "Affluent older shoppers",
    description: "Established older owners with time and money to spend.",
    bedRange: NA_BEDS,
  },
  {
    id: "students_and_young_singles",
    industry: "retail",
    label: "Students and young singles",
    description: "Students and young single renters. Value and convenience.",
    bedRange: NA_BEDS,
  },
  // leisure and fitness
  {
    id: "young_actives",
    industry: "leisure",
    label: "Young actives",
    description: "Younger members for gym and high-intensity classes.",
    bedRange: NA_BEDS,
  },
  {
    id: "active_families",
    industry: "leisure",
    label: "Active families",
    description: "Families using swimming, junior and family activities.",
    bedRange: NA_BEDS,
  },
  {
    id: "active_retirees",
    industry: "leisure",
    label: "Active retirees",
    description: "Older members for low-impact classes, swimming and racquets.",
    bedRange: NA_BEDS,
  },
  // healthcare and care
  {
    id: "families_and_children",
    industry: "healthcare",
    label: "Families and children",
    description: "Households with children, driving paediatric and GP demand.",
    bedRange: NA_BEDS,
  },
  {
    id: "working_age_adults",
    industry: "healthcare",
    label: "Working age adults",
    description: "Working age population for routine and occupational care.",
    bedRange: NA_BEDS,
  },
  {
    id: "older_adults_care",
    industry: "healthcare",
    label: "Older adults",
    description: "Older population with higher and longer-term care needs.",
    bedRange: NA_BEDS,
  },
  {
    id: "higher_needs_communities",
    industry: "healthcare",
    label: "Higher needs communities",
    description: "Areas of higher need, proxied by social-rented tenure.",
    bedRange: NA_BEDS,
  },
  // education
  {
    id: "early_years_primary",
    industry: "education",
    label: "Early years and primary",
    description: "Young families driving nursery and primary demand.",
    bedRange: NA_BEDS,
  },
  {
    id: "secondary_families",
    industry: "education",
    label: "Secondary families",
    description: "Households with teenagers, for secondary provision.",
    bedRange: NA_BEDS,
  },
  {
    id: "young_adults_he",
    industry: "education",
    label: "Young adults (HE and FE)",
    description: "Students and young adults for higher and further education.",
    bedRange: NA_BEDS,
  },
  {
    id: "adult_learners",
    industry: "education",
    label: "Adult learners",
    description: "Adults for community, vocational and lifelong learning.",
    bedRange: NA_BEDS,
  },
  // local authority / public sector
  {
    id: "families_households",
    industry: "public_sector",
    label: "Families and households",
    description: "Households with children, for family-facing services.",
    bedRange: NA_BEDS,
  },
  {
    id: "working_age_residents",
    industry: "public_sector",
    label: "Working age residents",
    description: "Working age population for employment and general services.",
    bedRange: NA_BEDS,
  },
  {
    id: "older_residents",
    industry: "public_sector",
    label: "Older residents",
    description: "Older residents for adult social care and accessibility.",
    bedRange: NA_BEDS,
  },
  {
    id: "deprivation_priority",
    industry: "public_sector",
    label: "Priority communities",
    description: "Higher-need communities, proxied by social-rented tenure.",
    bedRange: NA_BEDS,
  },
];

// The segments to show in a picker for a given industry. With no industry (admin
// or internal users, or a brand with none set) every segment is shown.
export function segmentsForIndustry(industry?: string | null): Segment[] {
  if (!industry) return SEGMENTS;
  const scoped = SEGMENTS.filter((s) => s.industry === industry);
  return scoped.length ? scoped : SEGMENTS;
}

// Look up a single segment by id across all industries (for display).
export function segmentById(id?: string | null): Segment | undefined {
  if (!id) return undefined;
  return SEGMENTS.find((s) => s.id === id);
}
