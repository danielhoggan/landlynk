// Browser-side client for the Next API routes. The routes proxy to the worker
// behind the Azure AD SSO gate.

import type { Battlecard } from "./types/battlecard";
import type { Catchment, CatchmentSummary } from "./types/catchment";

export interface SubmitPayload {
  kind: "postcode" | "gridref";
  value: string;
  developmentName: string;
  areaType?: "MSOA" | "LA";
  town?: string;
  strapline?: string;
  lifestylePillars?: string[];
  developmentFeatures?: string[];
  config?: {
    priceBand?: { from: number; to: number };
    bedRange?: string;
    driveTimeMinutes?: number;
    overlapThreshold?: number;
    catchmentMode?: string;
    radiusKm?: number;
    affordabilityMultiple?: number;
  };
}

export async function submitCatchment(
  payload: SubmitPayload,
): Promise<{ id: string }> {
  const res = await fetch("/api/catchments", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const detail = await res
      .json()
      .then((b) => b?.error ?? b?.detail)
      .catch(() => null);
    throw new Error(detail ?? `Submission failed (${res.status})`);
  }
  return res.json();
}

export async function getCatchment(id: string): Promise<Catchment> {
  const res = await fetch(`/api/catchments/${id}`);
  if (!res.ok) throw new Error(`Could not load catchment (${res.status})`);
  return res.json();
}

export async function listCatchments(
  archived = false,
): Promise<CatchmentSummary[]> {
  const res = await fetch(`/api/catchments?archived=${archived}`);
  if (!res.ok) throw new Error(`Could not load history (${res.status})`);
  return res.json();
}

export async function deleteCatchment(id: string): Promise<void> {
  const res = await fetch(`/api/catchments/${id}`, { method: "DELETE" });
  if (!res.ok) {
    if (res.status === 403) throw new Error("Only admins can delete runs");
    throw new Error(`Could not delete (${res.status})`);
  }
}

export async function archiveCatchment(
  id: string,
  archived: boolean,
): Promise<void> {
  const res = await fetch(`/api/catchments/${id}/archive`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ archived }),
  });
  if (!res.ok) throw new Error(`Could not archive (${res.status})`);
}

export async function getShares(id: string): Promise<string[]> {
  const res = await fetch(`/api/catchments/${id}/shares`);
  if (!res.ok) throw new Error(`Could not load shares (${res.status})`);
  return res.json();
}

export async function addShares(id: string, emails: string[]): Promise<void> {
  const res = await fetch(`/api/catchments/${id}/shares`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ emails }),
  });
  if (!res.ok) throw new Error(`Could not share (${res.status})`);
}

export async function removeShare(id: string, email: string): Promise<void> {
  const res = await fetch(
    `/api/catchments/${id}/shares/${encodeURIComponent(email)}`,
    { method: "DELETE" },
  );
  if (!res.ok) throw new Error(`Could not unshare (${res.status})`);
}

/** Download a combined Battlecard (selection or whole catchment) as a blob. */
export async function combinedExport(
  id: string,
  format: "pdf" | "pptx",
  body: { areaCodes?: string[]; scope: "selection" | "whole" },
): Promise<Blob> {
  const res = await fetch(`/api/catchments/${id}/combined/${format}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Could not build combined Battlecard (${res.status})`);
  return res.blob();
}

export interface AiModel {
  id: string;
  label: string;
  provider: string;
}

export async function getModels(): Promise<{
  models: AiModel[];
  default: string | null;
}> {
  const res = await fetch("/api/models");
  if (!res.ok) throw new Error(`Could not load models (${res.status})`);
  return res.json();
}

export async function setDefaultModel(model: string): Promise<void> {
  const res = await fetch("/api/models/default", {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ model }),
  });
  if (!res.ok) throw new Error(`Could not set model (${res.status})`);
}

export interface AreaProfile {
  description: string;
  amenities: { name: string; category: string }[];
  model?: string;
  cached?: boolean;
}

export async function generateAreaProfile(
  id: string,
  body: {
    scope: "selection" | "whole";
    areaCodes?: string[];
    model?: string;
    refresh?: boolean;
  },
): Promise<AreaProfile> {
  const res = await fetch(`/api/catchments/${id}/area-profile`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data?.error ?? `Could not generate profile (${res.status})`);
  }
  return data;
}

export interface AppUser {
  email: string | null;
  name: string | null;
  role: string;
}

export async function getMe(): Promise<AppUser> {
  const res = await fetch("/api/me");
  if (!res.ok) throw new Error(`Could not load account (${res.status})`);
  return res.json();
}

export async function getAccountSettings(): Promise<Record<
  string,
  unknown
> | null> {
  const res = await fetch("/api/me/settings");
  if (!res.ok) throw new Error(`Could not load settings (${res.status})`);
  const body = await res.json();
  return body?.settings ?? null;
}

export async function saveAccountSettings(
  settings: Record<string, unknown>,
): Promise<void> {
  const res = await fetch("/api/me/settings", {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ settings }),
  });
  if (!res.ok) throw new Error(`Could not save settings (${res.status})`);
}

export async function listUsers(): Promise<AppUser[]> {
  const res = await fetch("/api/users");
  if (!res.ok) throw new Error(`Could not load users (${res.status})`);
  return res.json();
}

export async function setUserRole(email: string, role: string): Promise<void> {
  const res = await fetch(`/api/users/${encodeURIComponent(email)}/role`, {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ role }),
  });
  if (!res.ok) throw new Error(`Could not update role (${res.status})`);
}

export interface ReferenceStatus {
  status: string;
  rows: number | null;
  error: string | null;
  updatedAt: string;
}

export async function getReferenceStatus(): Promise<
  Record<string, ReferenceStatus>
> {
  const res = await fetch("/api/admin/reference");
  if (!res.ok) throw new Error(`Could not load status (${res.status})`);
  return res.json();
}

export async function loadReference(
  dataset: string,
  params: Record<string, string>,
): Promise<void> {
  const res = await fetch(`/api/admin/reference/${dataset}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const detail = await res
      .json()
      .then((b) => b?.detail ?? b?.error)
      .catch(() => null);
    throw new Error(detail ?? `Load failed (${res.status})`);
  }
}

export async function getBattlecard(
  id: string,
  areaCode: string,
): Promise<Battlecard> {
  const res = await fetch(`/api/catchments/${id}/battlecards/${areaCode}`);
  if (!res.ok) throw new Error(`Could not load Battlecard (${res.status})`);
  return res.json();
}

/**
 * Poll a catchment until it reaches a terminal status. Catchment jobs run in the
 * worker, so the UI polls rather than blocking on the request.
 */
export async function pollCatchment(
  id: string,
  onUpdate: (c: Catchment) => void,
  {
    intervalMs = 1500,
    timeoutMs = 120_000,
  }: { intervalMs?: number; timeoutMs?: number } = {},
): Promise<Catchment> {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const catchment = await getCatchment(id);
    onUpdate(catchment);
    if (catchment.status === "complete" || catchment.status === "failed") {
      return catchment;
    }
    if (Date.now() > deadline) {
      throw new Error("Timed out waiting for the catchment to complete");
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
}
