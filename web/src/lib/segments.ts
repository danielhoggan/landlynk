// Audience segments for segment-first targeting. Mirrors the worker library in
// worker/src/landlynk_worker/scoring/segments.py; keep the ids in sync. The
// worker is the source of truth for the scoring vectors each segment applies.

export interface Segment {
  id: string;
  label: string;
  description: string;
  bedRange: string;
}

export const SEGMENTS: Segment[] = [
  {
    id: "first_time_buyer",
    label: "First time buyers",
    description: "Young renters stepping onto the ladder.",
    bedRange: "2 to 3",
  },
  {
    id: "second_stepper",
    label: "Second steppers",
    description: "Mortgaged owners trading up.",
    bedRange: "3 to 4",
  },
  {
    id: "growing_family",
    label: "Growing families",
    description: "Mid-life households with children.",
    bedRange: "3 to 5",
  },
  {
    id: "downsizer",
    label: "Downsizers",
    description: "Older outright owners releasing equity.",
    bedRange: "2 to 3",
  },
  {
    id: "high_net_worth",
    label: "High net worth",
    description: "Affluent established owners.",
    bedRange: "4 to 5",
  },
];
