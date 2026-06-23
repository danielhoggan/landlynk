"use client";

import { createContext, useContext, useEffect, useState } from "react";
import {
  getMe,
  getAccountSettings,
  getActiveBrandId,
  setActiveBrandId,
  type AppUser,
  type Brand,
} from "@/lib/client";
import { DEFAULT_SETTINGS, saveSettingsLocal } from "@/lib/settings";

interface UserContextValue {
  user: AppUser | null;
  isAdmin: boolean;
  /** Internal staff (admin or internal-user), never an external client user.
   * Gates staff-only tools such as the Marketing Activation pipeline. */
  isInternal: boolean;
  loading: boolean;
  /** Brands the user may switch between. */
  brands: Brand[];
  /** The active brand that white-labels the shell and scopes the session. */
  activeBrand: Brand | null;
  setActiveBrand: (builderId: string) => void;
}

const UserContext = createContext<UserContextValue>({
  user: null,
  isAdmin: false,
  isInternal: false,
  loading: true,
  brands: [],
  activeBrand: null,
  setActiveBrand: () => {},
});

const ROLE_KEY = "landlynk.role";
const ACTIVE_BRAND_OBJ_KEY = "landlynk.activeBrand";

// Loads the signed-in account once and shares role and brand selection across
// the app, so the nav can gate admin features and the shell white-labels to the
// active brand. Role and the active brand object are cached in localStorage and
// used as the initial value, so admin nav items and the brand logo do not flash
// on every navigation (each page load re-mounts this provider). Also hydrates
// the local settings cache from the account.
function cachedRole(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ROLE_KEY);
}

function cachedActiveBrand(): Brand | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(ACTIVE_BRAND_OBJ_KEY);
    return raw ? (JSON.parse(raw) as Brand) : null;
  } catch {
    return null;
  }
}

function rememberActiveBrand(brand: Brand | null): void {
  if (typeof window === "undefined") return;
  setActiveBrandId(brand?.builderId ?? null);
  if (brand) {
    window.localStorage.setItem(ACTIVE_BRAND_OBJ_KEY, JSON.stringify(brand));
  } else {
    window.localStorage.removeItem(ACTIVE_BRAND_OBJ_KEY);
  }
}

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(() => {
    const role = cachedRole();
    return role ? { email: null, name: null, role } : null;
  });
  const [brands, setBrands] = useState<Brand[]>([]);
  const [activeBrand, setActiveBrandState] = useState<Brand | null>(() =>
    cachedActiveBrand(),
  );
  const [loading, setLoading] = useState(true);

  function setActiveBrand(builderId: string) {
    const next = brands.find((b) => b.builderId === builderId) ?? null;
    if (next) {
      setActiveBrandState(next);
      rememberActiveBrand(next);
    }
  }

  useEffect(() => {
    let active = true;
    getMe()
      .then((u) => {
        if (!active) return;
        setUser(u);
        const list = u.brands ?? [];
        setBrands(list);
        if (typeof window !== "undefined" && u.role) {
          window.localStorage.setItem(ROLE_KEY, u.role);
        }
        // Keep the remembered brand if still accessible, else default to the
        // first alphabetically (the API returns brands sorted by name).
        const storedId = getActiveBrandId();
        const next =
          list.find((b) => b.builderId === storedId) ?? list[0] ?? null;
        setActiveBrandState(next);
        rememberActiveBrand(next);
      })
      .catch(() => {
        /* unauthenticated or worker down; nav simply hides admin items */
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    getAccountSettings()
      .then((s) => {
        if (s) saveSettingsLocal({ ...DEFAULT_SETTINGS, ...s });
      })
      .catch(() => {
        /* keep whatever is in local storage */
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <UserContext.Provider
      value={{
        user,
        isAdmin: user?.role === "admin",
        isInternal: user != null && user.role !== "external-user",
        loading,
        brands,
        activeBrand,
        setActiveBrand,
      }}
    >
      {children}
    </UserContext.Provider>
  );
}

export function useUser(): UserContextValue {
  return useContext(UserContext);
}
