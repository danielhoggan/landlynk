"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ChevronRight,
  Trash2,
  Archive,
  ArchiveRestore,
  Share2,
  X,
} from "lucide-react";
import type { CatchmentSummary } from "@/lib/types/catchment";
import {
  addShares,
  archiveCatchment,
  deleteCatchment,
  getShares,
  removeShare,
} from "@/lib/client";

interface Props {
  items: CatchmentSummary[];
  mode: "active" | "archived";
  isAdmin: boolean;
  onChanged: (id: string) => void;
  onError: (message: string) => void;
}

// Shared list of catchments with per-row actions. History shows active runs and
// Archived shows archived ones. Owners (and admins) can share and archive;
// only admins can delete.
export function CatchmentList({
  items,
  mode,
  isAdmin,
  onChanged,
  onError,
}: Props) {
  const [busy, setBusy] = useState<string | null>(null);
  const [sharing, setSharing] = useState<string | null>(null);

  async function onArchive(id: string, archived: boolean) {
    setBusy(id);
    try {
      await archiveCatchment(id, archived);
      onChanged(id);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(null);
    }
  }

  async function onDelete(id: string, name: string) {
    if (!confirm(`Delete the catchment for "${name}"? This cannot be undone.`)) {
      return;
    }
    setBusy(id);
    try {
      await deleteCatchment(id);
      onChanged(id);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <ol className="divide-y divide-neutral-200 overflow-hidden rounded-card border border-neutral-200 bg-white">
      {items.map((item) => (
        <li key={item.id}>
          <div className="flex items-center gap-2 px-4 py-3">
            <Link
              href={`/?catchment=${item.id}`}
              className="flex min-w-0 flex-1 items-center gap-3 transition-colors hover:opacity-80"
            >
              <span className="min-w-0 flex-1">
                <span className="flex items-center gap-2">
                  <span className="truncate text-sm font-semibold">
                    {item.developmentName?.trim()
                      ? `${item.developmentName} · ${item.inputValue}`
                      : item.inputValue}
                  </span>
                  {item.shared && (
                    <span className="rounded-full bg-light-accent/10 px-2 py-0.5 text-[10px] font-medium text-light-accent">
                      Shared with you
                    </span>
                  )}
                </span>
                <span className="block text-xs text-neutral-500">
                  {item.status} - {item.areaCount} areas
                  {item.createdAt
                    ? ` - ${new Date(item.createdAt).toLocaleDateString("en-GB")}`
                    : ""}
                  {item.shared && item.owner ? ` - by ${item.owner}` : ""}
                </span>
              </span>
              <ChevronRight size={18} className="shrink-0 text-neutral-400" />
            </Link>

            <div className="flex shrink-0 items-center gap-1">
              {!item.shared && (
                <IconButton
                  label="Share"
                  onClick={() => setSharing(sharing === item.id ? null : item.id)}
                >
                  <Share2 size={16} />
                </IconButton>
              )}
              {mode === "active" ? (
                <IconButton
                  label="Archive"
                  disabled={busy === item.id}
                  onClick={() => onArchive(item.id, true)}
                >
                  <Archive size={16} />
                </IconButton>
              ) : (
                <IconButton
                  label="Restore"
                  disabled={busy === item.id}
                  onClick={() => onArchive(item.id, false)}
                >
                  <ArchiveRestore size={16} />
                </IconButton>
              )}
              {isAdmin && (
                <IconButton
                  label="Delete"
                  danger
                  disabled={busy === item.id}
                  onClick={() => onDelete(item.id, item.developmentName)}
                >
                  <Trash2 size={16} />
                </IconButton>
              )}
            </div>
          </div>

          {sharing === item.id && (
            <SharePanel
              catchmentId={item.id}
              onError={onError}
              onClose={() => setSharing(null)}
            />
          )}
        </li>
      ))}
    </ol>
  );
}

function IconButton({
  label,
  onClick,
  children,
  danger,
  disabled,
}: {
  label: string;
  onClick: () => void;
  children: React.ReactNode;
  danger?: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      disabled={disabled}
      className={`rounded-card p-2 transition-colors disabled:opacity-40 ${
        danger
          ? "text-neutral-400 hover:bg-priority-low/10 hover:text-priority-low"
          : "text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700"
      }`}
    >
      {children}
    </button>
  );
}

function SharePanel({
  catchmentId,
  onError,
  onClose,
}: {
  catchmentId: string;
  onError: (m: string) => void;
  onClose: () => void;
}) {
  const [emails, setEmails] = useState<string[] | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  // Load the current shares when the panel opens.
  useEffect(() => {
    getShares(catchmentId)
      .then(setEmails)
      .catch(() => setEmails([]));
  }, [catchmentId]);

  async function add() {
    const value = input.trim().toLowerCase();
    if (!value) return;
    setBusy(true);
    try {
      await addShares(catchmentId, [value]);
      setEmails((prev) => [...new Set([...(prev ?? []), value])]);
      setInput("");
    } catch (e) {
      onError(e instanceof Error ? e.message : "Share failed");
    } finally {
      setBusy(false);
    }
  }

  async function remove(email: string) {
    setBusy(true);
    try {
      await removeShare(catchmentId, email);
      setEmails((prev) => (prev ?? []).filter((e) => e !== email));
    } catch (e) {
      onError(e instanceof Error ? e.message : "Unshare failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="border-t border-neutral-200 bg-neutral-50 px-4 py-3">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs font-medium text-neutral-600">
          Share with colleagues
        </p>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close share"
          className="text-neutral-400 hover:text-neutral-700"
        >
          <X size={14} />
        </button>
      </div>
      <div className="flex gap-2">
        <input
          type="email"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && add()}
          placeholder="colleague@email.com"
          className="w-full rounded-card border border-neutral-300 px-3 py-1.5 text-xs outline-none focus:border-light-accent focus:ring-2 focus:ring-light-accent/20"
        />
        <button
          type="button"
          onClick={add}
          disabled={busy}
          className="rounded-card bg-light-accent px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-50"
        >
          Add
        </button>
      </div>
      {emails && emails.length > 0 && (
        <ul className="mt-2 flex flex-wrap gap-2">
          {emails.map((email) => (
            <li
              key={email}
              className="flex items-center gap-1 rounded-full bg-white px-2 py-0.5 text-xs"
            >
              {email}
              <button
                type="button"
                onClick={() => remove(email)}
                aria-label={`Remove ${email}`}
                className="text-neutral-400 hover:text-priority-low"
              >
                <X size={12} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
