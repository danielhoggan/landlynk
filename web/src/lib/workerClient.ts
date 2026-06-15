import type { Catchment, CatchmentSummary } from "./types/catchment";
import type { Battlecard } from "./types/battlecard";

// Thin client for the Python worker service. The API route handlers stay thin
// (CLAUDE.md, architecture rules): they submit jobs and read results. All heavy
// geospatial work happens in the worker, never in a Next.js request cycle.
//
// The worker is private and trusts the signed-in identity the SSO-gated web
// layer forwards. Every call the worker scopes by user passes the caller's
// email and name as headers.

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

export interface UserCtx {
  email?: string | null;
  name?: string | null;
}

export interface AppUser {
  email: string | null;
  name: string | null;
  role: string;
}

export function userHeaders(user?: UserCtx): Record<string, string> {
  const headers: Record<string, string> = {};
  if (user?.email) headers["X-User-Email"] = user.email;
  if (user?.name) headers["X-User-Name"] = user.name;
  return headers;
}

// Forward the caller's active brand to the worker, which scopes profiles and the
// AI allowance to that brand's group.
export function activeBrandHeader(request: Request): Record<string, string> {
  const id = request.headers.get("x-active-brand");
  return id ? { "X-Active-Brand": id } : {};
}

async function workerFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${WORKER_BASE_URL}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    // Surface the worker's error detail (e.g. a database or geocode failure)
    // rather than a bare status, so the UI can show what actually went wrong.
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail ?? body?.error ?? detail;
    } catch {
      /* non-JSON body, keep statusText */
    }
    throw new Error(`Worker ${res.status}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

/** Submit a catchment job. The worker geocodes, builds the isochrone, etc. */
export function submitCatchmentJob(
  input: Record<string, unknown>,
  user?: UserCtx,
): Promise<{ id: string }> {
  return workerFetch("/jobs/catchment", {
    method: "POST",
    body: JSON.stringify(input),
    headers: userHeaders(user),
  });
}

/** Read a catchment and its scored, ranked areas. */
export function getCatchment(id: string, user?: UserCtx): Promise<Catchment> {
  return workerFetch(`/catchments/${id}`, { headers: userHeaders(user) });
}

/** List catchments visible to the caller (own plus shared), active or archived. */
export function listCatchments(
  user?: UserCtx,
  archived = false,
): Promise<CatchmentSummary[]> {
  return workerFetch(`/catchments?archived=${archived}`, {
    headers: userHeaders(user),
  });
}

/** Read one area's stored Battlecard payload. No recompute needed. */
export function getBattlecard(
  catchmentId: string,
  areaCode: string,
  user?: UserCtx,
): Promise<Battlecard> {
  return workerFetch(`/catchments/${catchmentId}/battlecards/${areaCode}`, {
    headers: userHeaders(user),
  });
}

/** Delete a catchment. Admin only (enforced by the worker). */
export function deleteCatchmentJob(id: string, user?: UserCtx): Promise<void> {
  return workerFetch(`/catchments/${id}`, {
    method: "DELETE",
    headers: userHeaders(user),
  });
}

/** Archive or unarchive a catchment. Owner or admin. */
export function setArchived(
  id: string,
  archived: boolean,
  user?: UserCtx,
): Promise<void> {
  return workerFetch(
    `/catchments/${id}/${archived ? "archive" : "unarchive"}`,
    { method: "POST", headers: userHeaders(user) },
  );
}

export function listShares(id: string, user?: UserCtx): Promise<string[]> {
  return workerFetch(`/catchments/${id}/shares`, { headers: userHeaders(user) });
}

export function addShares(
  id: string,
  emails: string[],
  user?: UserCtx,
): Promise<void> {
  return workerFetch(`/catchments/${id}/shares`, {
    method: "POST",
    body: JSON.stringify({ emails }),
    headers: userHeaders(user),
  });
}

export function removeShare(
  id: string,
  email: string,
  user?: UserCtx,
): Promise<void> {
  return workerFetch(`/catchments/${id}/shares/${encodeURIComponent(email)}`, {
    method: "DELETE",
    headers: userHeaders(user),
  });
}

/** The caller's account record (email, name, role), upserted on read. */
export function getMe(user?: UserCtx): Promise<AppUser> {
  return workerFetch("/me", { headers: userHeaders(user) });
}

export function getMySettings(
  user?: UserCtx,
): Promise<{ settings: Record<string, unknown> | null }> {
  return workerFetch("/me/settings", { headers: userHeaders(user) });
}

export function putMySettings(
  settings: Record<string, unknown>,
  user?: UserCtx,
): Promise<void> {
  return workerFetch("/me/settings", {
    method: "PUT",
    body: JSON.stringify({ settings }),
    headers: userHeaders(user),
  });
}

/** List all users. Admin only. */
export function listUsers(user?: UserCtx): Promise<AppUser[]> {
  return workerFetch("/admin/users", { headers: userHeaders(user) });
}

export function setUserRole(
  email: string,
  role: string,
  user?: UserCtx,
): Promise<void> {
  return workerFetch(`/admin/users/${encodeURIComponent(email)}/role`, {
    method: "PUT",
    body: JSON.stringify({ role }),
    headers: userHeaders(user),
  });
}
