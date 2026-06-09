"use client";

import { useEffect, useState } from "react";
import { Users } from "lucide-react";
import { listUsers, setUserRole, type AppUser } from "@/lib/client";
import { useUser } from "@/lib/userContext";

const ROLES = ["admin", "internal-user", "external-user"];

const ROLE_LABELS: Record<string, string> = {
  admin: "Admin",
  "internal-user": "Internal user",
  "external-user": "External user",
};

// Admin-only user directory. Admins set roles. Roles govern permissions: admins
// delete runs and manage users; everyone else archives and shares their own.
export default function UsersPage() {
  const { user, isAdmin, loading } = useUser();
  const [users, setUsers] = useState<AppUser[] | null>(null);
  const [error, setError] = useState("");
  const [savingEmail, setSavingEmail] = useState<string | null>(null);

  useEffect(() => {
    if (!isAdmin) return;
    listUsers()
      .then(setUsers)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load"),
      );
  }, [isAdmin]);

  if (loading) {
    return <p className="p-4 text-sm text-neutral-500">Loading...</p>;
  }

  if (!isAdmin) {
    return (
      <div className="mx-auto max-w-2xl p-4">
        <p className="rounded-card border border-neutral-200 bg-white p-4 text-sm text-neutral-600">
          This page is for admins only.
        </p>
      </div>
    );
  }

  async function changeRole(email: string, role: string) {
    setSavingEmail(email);
    setError("");
    try {
      await setUserRole(email, role);
      setUsers((prev) =>
        prev ? prev.map((u) => (u.email === email ? { ...u, role } : u)) : prev,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Update failed");
    } finally {
      setSavingEmail(null);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4">
      <h1 className="flex items-center gap-2 text-lg font-semibold">
        <Users size={20} /> Users
      </h1>
      <p className="text-sm text-neutral-500">
        Roles govern access. Admins delete runs and manage users; internal and
        external users build, share and archive their own catchments.
      </p>

      {error && <p className="text-sm text-priority-low">{error}</p>}
      {users === null && !error && (
        <p className="text-sm text-neutral-500">Loading...</p>
      )}

      {users && (
        <ul className="divide-y divide-neutral-200 overflow-hidden rounded-card border border-neutral-200 bg-white">
          {users.map((u) => (
            <li
              key={u.email}
              className="flex items-center gap-3 px-4 py-3"
            >
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-semibold">
                  {u.name || u.email}
                  {u.email === user?.email && (
                    <span className="ml-2 text-xs font-normal text-neutral-400">
                      you
                    </span>
                  )}
                </span>
                <span className="block truncate text-xs text-neutral-500">
                  {u.email}
                </span>
              </span>
              <select
                value={u.role}
                disabled={savingEmail === u.email}
                onChange={(e) => changeRole(u.email as string, e.target.value)}
                className="rounded-card border border-neutral-300 bg-white px-2 py-1.5 text-sm outline-none focus:border-light-accent focus:ring-2 focus:ring-light-accent/20 disabled:opacity-50"
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {ROLE_LABELS[r]}
                  </option>
                ))}
              </select>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
