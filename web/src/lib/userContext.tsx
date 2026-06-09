"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { getMe, getAccountSettings, type AppUser } from "@/lib/client";
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

// Loads the signed-in account once and shares role across the app, so the nav
// and pages can gate admin features. The role is cached in localStorage and used
// as the initial value, so admin nav items do not flash in on every navigation
// (each page load re-mounts this provider). Also hydrates the local settings
// cache from the account so the catchment form seeds from per-account defaults.
function cachedRole(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ROLE_KEY);
}

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(() => {
    const role = cachedRole();
    return role ? { email: null, name: null, role } : null;
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    getMe()
      .then((u) => {
        if (active) {
          setUser(u);
          if (typeof window !== "undefined" && u.role) {
            window.localStorage.setItem(ROLE_KEY, u.role);
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
