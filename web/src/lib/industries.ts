// Client sectors. Set per group in the Brands admin area; used to tailor the
// How it works page to the company's industry rather than showing the generic,
// all-sectors version. Keep ids stable: they are stored on the group.
export interface Industry {
  id: string;
  label: string;
}

export const INDUSTRIES: Industry[] = [
  { id: "residential", label: "Residential development / house building" },
  { id: "retail", label: "Retail and hospitality" },
  { id: "leisure", label: "Leisure and fitness" },
  { id: "healthcare", label: "Healthcare and care" },
  { id: "education", label: "Education" },
  { id: "public_sector", label: "Local authority / public sector" },
];

export function industryLabel(id: string | null | undefined): string | null {
  if (!id) return null;
  return INDUSTRIES.find((i) => i.id === id)?.label ?? null;
}
