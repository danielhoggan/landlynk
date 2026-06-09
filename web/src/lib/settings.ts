// User-tunable defaults, persisted in the browser. These seed the catchment
// form and are the baseline a saved run's stored config is compared against, so
// a run built under different assumptions can be flagged. They are defaults
// only: the values actually used are always stored with each catchment by the
// worker, which remains the source of truth for reproducibility.

export interface AppSettings {
  /** Show the LA area-level option in the catchment form. MSOA is the default. */
  enableLA: boolean;
  /** Gross household income multiple used to imply an affordable price. */
  affordabilityMultiple: number;
  /** Minimum area overlap with the isochrone to retain it, 0 to 1. */
  overlapThreshold: number;
  /** Scoring signal weights. Need not sum to 1; normalised server-side. */
  weights: {
    income_fit: number;
    tenure_signal: number;
    age_skew: number;
    addressable_scale: number;
    household_type: number;
  };
}

// Mirrors the worker ScoringConfig defaults (scoring/profile.py).
export const DEFAULT_SETTINGS: AppSettings = {
  enableLA: false,
  affordabilityMultiple: 4.5,
  overlapThreshold: 0.1,
  weights: {
    income_fit: 0.3,
    tenure_signal: 0.2,
    age_skew: 0.2,
    addressable_scale: 0.2,
    household_type: 0.1,
  },
};

const KEY = "landlynk.settings";

export function loadSettings(): AppSettings {
  if (typeof window === "undefined") return DEFAULT_SETTINGS;
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return DEFAULT_SETTINGS;
    const parsed = JSON.parse(raw) as Partial<AppSettings>;
    return {
      enableLA: parsed.enableLA ?? DEFAULT_SETTINGS.enableLA,
      affordabilityMultiple:
        parsed.affordabilityMultiple ?? DEFAULT_SETTINGS.affordabilityMultiple,
      overlapThreshold:
        parsed.overlapThreshold ?? DEFAULT_SETTINGS.overlapThreshold,
      weights: { ...DEFAULT_SETTINGS.weights, ...(parsed.weights ?? {}) },
    };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

/** Write the local cache. The account is the source of truth; this cache lets
 * the catchment form seed synchronously without an async round trip. */
export function saveSettingsLocal(settings: AppSettings): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEY, JSON.stringify(settings));
}

// Backwards-compatible alias.
export const saveSettings = saveSettingsLocal;
