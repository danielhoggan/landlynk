"use client";

import { createContext, useContext, useEffect, useState } from "react";
import {
  getMe,
  getAccountSettings,
  type AppUser,
  type Brand,
} from "@/lib/client";
import { DEFAULT_SETTINGS, saveSettingsLocal } from "@/lib/settings";

interface UserContextValue {
  user: AppUser | null;
  isAdmin: boolean;
  loading: boolean;
}

const UserContext = createContext<UserContextValue>({
  user: null,
  isAdmin: false,
  loading: true,
});

const ROLE_KEY = "landlynk.role";
const BRAND_KEY = "landlynk.brand";

// Loads the signed-in account once and shares role and brand across the app, so
// the nav can gate admin features and the shell can white-label. Both are cached
// in localStorage and used as the initial value, so admin nav items and the
// brand logo do not flash on every navigation (each page load re-mounts this
// provider). Also hydrates the local settings cache from the account so the
// catchment form seeds from per-account defaults.
function cachedRole(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ROLE_KEY);
}

function cachedBrand(): Brand | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(BRAND_KEY);
    return raw ? (JSON.parse(raw) as Brand) : null;
  } catch {
    return null;
  }
}

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(() => {
    const role = cachedRole();
    return role ? { email: null, name: null, role, brand: cachedBrand() } : null;
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    getMe()
      .then((u) => {
        if (active) {
          setUser(u);
          if (typeof window !== "undefined") {
            if (u.role) window.localStorage.setItem(ROLE_KEY, u.role);
            if (u.brand) {
              window.localStorage.setItem(BRAND_KEY, JSON.stringify(u.brand));
            } else {
              window.localStorage.removeItem(BRAND_KEY);
            }
          }
        }
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
      value={{ user, isAdmin: user?.role === "admin", loading }}
    >
      {children}
    </UserContext.Provider>
  );
}

export function useUser(): UserContextValue {
  return useContext(UserContext);
}
