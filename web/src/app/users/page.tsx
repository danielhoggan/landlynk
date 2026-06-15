"use client";

import { useEffect, useState } from "react";
import { Users } from "lucide-react";
import {
  listUsers,
  setUserRole,
  listGroups,
  setUserGroup,
  listBuilders,
  getUserBrands,
  setUserBrands,
  type AppUser,
  type BuilderGroup,
  type Builder,
} from "@/lib/client";
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
  const [groups, setGroups] = useState<BuilderGroup[]>([]);
  const [builders, setBuilders] = useState<Builder[]>([]);
  const [error, setError] = useState("");
  const [savingEmail, setSavingEmail] = useState<string | null>(null);

  useEffect(() => {
    if (!isAdmin) return;
    listUsers()
      .then(setUsers)
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Failed to load"),
      );
    listGroups()
      .then(setGroups)
      .catch(() => setGroups([]));
    listBuilders()
      .then(setBuilders)
      .catch(() => setBuilders([]));
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

  async function changeGroup(email: string, groupId: string) {
    setSavingEmail(email);
    setError("");
    try {
      await setUserGroup(email, groupId || null);
      setUsers((prev) =>
        prev
          ? prev.map((u) =>
              u.email === email ? { ...u, builderGroupId: groupId || null } : u,
            )
          : prev,
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

      <p className="text-xs text-neutral-400">
        Give an external user a whole group (all its brands) and/or assign
        specific brands. They switch the active brand in the app.
      </p>

      {users && (
        <ul className="divide-y divide-neutral-200 overflow-visible rounded-card border border-neutral-200 bg-white">
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
              {u.role === "external-user" && (
                <>
                  <select
                    value={u.builderGroupId ?? ""}
                    disabled={savingEmail === u.email}
                    onChange={(e) =>
                      changeGroup(u.email as string, e.target.value)
                    }
                    title="Whole-group access (all the group's brands)"
                    className="rounded-card border border-neutral-300 bg-white px-2 py-1.5 text-sm outline-none focus:border-light-accent disabled:opacity-50"
                  >
                    <option value="">No group</option>
                    {groups.map((g) => (
                      <option key={g.id} value={g.id}>
                        {g.name}
                      </option>
                    ))}
                  </select>
                  <BrandAssign
                    email={u.email as string}
                    builders={builders}
                    groups={groups}
                  />
                </>
              )}
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

// Assign a user to specific brands (a business unit), across groups. Independent
// of the whole-group grant. Loads the current grants when opened.
function BrandAssign({
  email,
  builders,
  groups,
}: {
  email: string;
  builders: Builder[];
  groups: BuilderGroup[];
}) {
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<string[] | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (open && selected === null) {
      getUserBrands(email)
        .then(setSelected)
        .catch(() => setSelected([]));
    }
  }, [open, email, selected]);

  const groupName = (id: string) =>
    groups.find((g) => g.id === id)?.name ?? "Other";
  const count = selected?.length ?? 0;

  function toggle(id: string) {
    setSelected((s) =>
      s
        ? s.includes(id)
          ? s.filter((x) => x !== id)
          : [...s, id]
        : [id],
    );
  }

  async function save() {
    if (!selected) return;
    setSaving(true);
    try {
      await setUserBrands(email, selected);
      setOpen(false);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="rounded-card border border-neutral-300 bg-white px-2 py-1.5 text-sm text-neutral-700 hover:border-light-accent"
        title="Assign specific brands"
      >
        Brands{count ? ` (${count})` : ""}
      </button>
      {open && (
        <div className="absolute right-0 z-20 mt-1 w-64 rounded-card border border-neutral-200 bg-white p-2 shadow-lg">
          {selected === null ? (
            <p className="p-2 text-xs text-neutral-500">Loading...</p>
          ) : builders.length === 0 ? (
            <p className="p-2 text-xs text-neutral-500">No brands yet.</p>
          ) : (
            <div className="max-h-64 space-y-1 overflow-auto">
              {builders.map((b) => (
                <label
                  key={b.id}
                  className="flex items-center gap-2 rounded px-1.5 py-1 text-xs hover:bg-neutral-50"
                >
                  <input
                    type="checkbox"
                    checked={selected.includes(b.id)}
                    onChange={() => toggle(b.id)}
                  />
                  <span className="truncate">
                    {b.name}
                    <span className="text-neutral-400">
                      {" "}
                      · {groupName(b.groupId)}
                    </span>
                  </span>
                </label>
              ))}
            </div>
          )}
          <div className="mt-2 flex justify-end gap-2 border-t border-neutral-100 pt-2">
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="rounded-card px-2 py-1 text-xs text-neutral-500"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={save}
              disabled={saving || selected === null}
              className="rounded-card bg-light-accent px-2 py-1 text-xs font-semibold text-white disabled:opacity-50"
            >
              Save
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
