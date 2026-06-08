import type { Catchment, CatchmentSummary } from "./types/catchment";
import type { Battlecard } from "./types/battlecard";

// Thin client for the Python worker service. The API route handlers stay thin
// (CLAUDE.md, architecture rules): they submit jobs and read results. All heavy
// geospatial work happens in the worker, never in a Next.js request cycle.

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

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
  return res.json() as Promise<T>;
}

/** Submit a catchment job. The worker geocodes, builds the isochrone, etc. The
 * request body is the development brief and scoring config; the worker validates
 * it. */
export function submitCatchmentJob(
  input: Record<string, unknown>,
): Promise<{ id: string }> {
  return workerFetch("/jobs/catchment", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

/** Read a catchment and its scored, ranked areas. */
export function getCatchment(id: string): Promise<Catchment> {
  return workerFetch(`/catchments/${id}`);
}

/** List recent catchments for the history view. */
export function listCatchments(): Promise<CatchmentSummary[]> {
  return workerFetch("/catchments");
}

/** Delete a catchment and its stored areas and Battlecards. */
export async function deleteCatchmentJob(id: string): Promise<void> {
  const res = await fetch(`${WORKER_BASE_URL}/catchments/${id}`, {
    method: "DELETE",
    cache: "no-store",
  });
  if (!res.ok && res.status !== 404) {
    throw new Error(`Worker delete failed: ${res.status}`);
  }
}

/** Read one area's stored Battlecard payload. No recompute needed. */
export function getBattlecard(
  catchmentId: string,
  areaCode: string,
): Promise<Battlecard> {
  return workerFetch(`/catchments/${catchmentId}/battlecards/${areaCode}`);
}
