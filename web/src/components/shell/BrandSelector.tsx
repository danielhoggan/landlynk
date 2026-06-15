"use client";

import { useUser } from "@/lib/userContext";

// Lets a user who can access more than one brand switch the active brand. The
// active brand white-labels the shell and scopes profiles and the AI allowance,
// so on change we reload to re-scope everything consistently. Hidden for users
// with one brand or none.
export function BrandSelector() {
  const { brands, activeBrand, setActiveBrand } = useUser();
  if (brands.length < 2) return null;

  return (
    <div className="px-2">
      <label htmlFor="brand-selector" className="sr-only">
        Active brand
      </label>
      <select
        id="brand-selector"
        value={activeBrand?.builderId ?? ""}
        onChange={(e) => {
          setActiveBrand(e.target.value);
          window.location.reload();
        }}
        className="w-full rounded-card border border-neutral-200 bg-white px-2 py-1.5 text-xs font-medium text-neutral-700"
        title="Switch the active brand"
      >
        {brands.map((b) => (
          <option key={b.builderId} value={b.builderId ?? ""}>
            {b.name}
          </option>
        ))}
      </select>
    </div>
  );
}
