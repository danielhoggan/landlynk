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
    segment?: string;
    brandHeading?: string;
    brandSecondary?: string;
    brandAccent?: string;
    brandLogoPath?: string;
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

/** Download the full multi-slide report deck (selection or whole catchment). */
export async function reportExport(
  id: string,
  body: { areaCodes?: string[]; scope: "selection" | "whole" },
): Promise<Blob> {
  const res = await fetch(`/api/catchments/${id}/report/pptx`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Could not build report (${res.status})`);
  return res.blob();
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

// Read an already-cached whole-catchment profile without generating or metering.
// Returns null when none is cached, so the panel can auto-show a prior snapshot.
export async function getCachedAreaProfile(
  id: string,
): Promise<AreaProfile | null> {
  const res = await fetch(`/api/catchments/${id}/area-profile`, {
    headers: activeBrandHeaders(),
  });
  if (!res.ok) return null;
  const data = await res.json().catch(() => ({ profile: null }));
  return data?.profile ?? null;
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
    headers: { "content-type": "application/json", ...activeBrandHeaders() },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data?.error ?? `Could not generate profile (${res.status})`);
  }
  return data;
}

export interface BuilderProfile {
  id: string;
  builderId: string;
  name: string;
  segment?: string | null;
  bedRange?: string | null;
  priceFrom?: number | null;
  priceTo?: number | null;
  strapline?: string | null;
  pillars: string[];
  features: string[];
  builderName?: string;
  themeHeading?: string;
  themeSecondary?: string | null;
  themeAccent?: string | null;
  logoPath?: string | null;
  fonts?: string[];
  groupId?: string;
  groupName?: string;
  /** The brand's best / target locations (postcodes), for lookalike weighting. */
  targetLocations?: string[];
}

export interface BuilderGroup {
  id: string;
  name: string;
  monthlyCap?: number | null;
  /** Monthly catchment-run allowance, pooled per group. Null means unlimited. */
  monthlyJobCap?: number | null;
  /** The client's sector, used to tailor explanatory content (How it works). */
  industry?: string | null;
}

/** A monthly allowance and how much of it has been used (AI or runs). */
export interface UsageAllowance {
  period?: string;
  metered: boolean;
  cap?: number | null;
  used?: number;
  remaining?: number | null;
  /** ISO date the monthly allowance resets (the 1st of next month). */
  resetsOn?: string;
}

export interface LlmUsage extends UsageAllowance {
  model?: string | null;
  estCost?: number;
  /** The monthly catchment-run allowance, alongside this AI allowance. */
  jobs?: UsageAllowance;
}

export interface CostRow {
  actorEmail?: string;
  model?: string;
  groupId?: string | null;
  groupName?: string;
  generations: number;
  cost: number;
  tokens: number;
}

export interface CostItem {
  createdAt: string | null;
  actorEmail: string | null;
  catchmentId: string | null;
  model: string | null;
  groupName?: string;
  tokens?: number;
  cost: number;
}

export interface CostReport {
  total: number;
  tokens: number;
  generations: number;
  byUser: CostRow[];
  byModel: CostRow[];
  byGroup: CostRow[];
  items: CostItem[];
}

export async function getCosts(filters: {
  dateFrom?: string;
  dateTo?: string;
}): Promise<CostReport> {
  const qs = new URLSearchParams();
  if (filters.dateFrom) qs.set("date_from", filters.dateFrom);
  if (filters.dateTo) qs.set("date_to", filters.dateTo);
  const res = await fetch(`/api/admin/costs?${qs.toString()}`);
  if (!res.ok) throw new Error(`Could not load costs (${res.status})`);
  return res.json();
}

export interface CatchmentVerdict {
  priceFit: "within" | "stretch" | "above" | "unknown";
  /** Whether the run carried an explicit target price (vs the engine default). */
  priceSet: boolean;
  priceFrom: number | null;
  impliedAffordablePrice: number | null;
  positioning: string;
  population: number | null;
  households: number | null;
  medianHousePrice: number | null;
  segments: {
    firstTimeBuyer: number | null;
    downsizer: number | null;
    family: number | null;
  };
  confidence: "high" | "medium" | "low";
}

// The whole-catchment appraisal verdict (price fit + addressable demand), used
// by the housebuilder appraise and next-phase intents.
export async function getCatchmentVerdict(
  catchmentId: string,
): Promise<CatchmentVerdict | null> {
  const res = await fetch(`/api/catchments/${catchmentId}/verdict`, {
    method: "POST",
    headers: { "content-type": "application/json", ...activeBrandHeaders() },
    body: JSON.stringify({ scope: "whole" }),
  });
  if (!res.ok) return null;
  return res.json();
}

export interface DevelopmentSite {
  reference: string | null;
  name: string | null;
  hectares: number | null;
  minDwellings: number | null;
  maxDwellings: number | null;
  lat: number;
  lng: number;
  /** The MSOA/LA the site falls in, for per-area listing. */
  areaCode: string | null;
}

// Brownfield development sites inside a catchment, for the Find a site overlay.
export async function getCatchmentSites(
  catchmentId: string,
): Promise<DevelopmentSite[]> {
  const res = await fetch(`/api/catchments/${catchmentId}/sites`, {
    headers: activeBrandHeaders(),
  });
  if (!res.ok) return [];
  const data = await res.json().catch(() => ({ sites: [] }));
  return data?.sites ?? [];
}

export async function getUsage(): Promise<LlmUsage> {
  const res = await fetch("/api/builders/usage", {
    headers: activeBrandHeaders(),
  });
  if (!res.ok) return { metered: false };
  return res.json();
}

export async function updateGroup(
  id: string,
  body: {
    name?: string;
    monthlyCap?: number | null;
    monthlyJobCap?: number | null;
    industry?: string | null;
  },
): Promise<void> {
  const res = await fetch(`/api/admin/builders/groups/${id}`, {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Could not update group (${res.status})`);
}

export interface Builder {
  id: string;
  groupId: string;
  name: string;
  themeHeading: string;
  themeSecondary?: string | null;
  themeAccent?: string | null;
  fonts?: string[];
  logoPath?: string | null;
  /** Best / target locations (postcodes) for lookalike weighting. */
  targetLocations?: string[];
  /** The brand's sector, used to tailor segments and How it works. */
  industry?: string | null;
}

// The specific brand grants for a user (separate from a whole-group grant).
export async function getUserBrands(email: string): Promise<string[]> {
  const res = await fetch(
    `/api/admin/users/${encodeURIComponent(email)}/brands`,
  );
  if (!res.ok) return [];
  const data = await res.json().catch(() => ({ brandIds: [] }));
  return data?.brandIds ?? [];
}

// Assign a user to specific brands they can switch between.
export async function setUserBrands(
  email: string,
  brandIds: string[],
): Promise<void> {
  const res = await fetch(
    `/api/admin/users/${encodeURIComponent(email)}/brands`,
    {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ brandIds }),
    },
  );
  if (!res.ok) throw new Error(`Could not assign brands (${res.status})`);
}

export async function uploadBrandLogo(
  builderId: string,
  filename: string,
  base64: string,
): Promise<void> {
  const res = await fetch(`/api/admin/builders/${builderId}/logo`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ filename, content: base64 }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data?.error ?? `Could not upload logo (${res.status})`);
  }
}

async function jsonOrThrow<T>(res: Response, what: string): Promise<T> {
  if (!res.ok) throw new Error(`${what} (${res.status})`);
  return res.json();
}

export async function getBuilderProfiles(): Promise<BuilderProfile[]> {
  return jsonOrThrow(
    await fetch("/api/builders/profiles", { headers: activeBrandHeaders() }),
    "Could not load profiles",
  );
}

export async function listGroups(): Promise<BuilderGroup[]> {
  return jsonOrThrow(await fetch("/api/admin/builders/groups"), "Could not load groups");
}

export async function createGroup(
  name: string,
  industry?: string | null,
): Promise<BuilderGroup> {
  return jsonOrThrow(
    await fetch("/api/admin/builders/groups", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ name, industry: industry ?? null }),
    }),
    "Could not create group",
  );
}

export async function deleteGroup(id: string): Promise<void> {
  await fetch(`/api/admin/builders/groups/${id}`, { method: "DELETE" });
}

export async function listBuilders(groupId?: string): Promise<Builder[]> {
  const q = groupId ? `?groupId=${encodeURIComponent(groupId)}` : "";
  return jsonOrThrow(await fetch(`/api/admin/builders${q}`), "Could not load brands");
}

export async function createBuilder(body: {
  groupId: string;
  name: string;
  themeHeading: string;
  themeSecondary?: string;
  themeAccent?: string;
  fonts?: string[];
  targetLocations?: string[];
  industry?: string | null;
}): Promise<{ id: string }> {
  return jsonOrThrow(
    await fetch("/api/admin/builders", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Could not create brand",
  );
}

// Edit a saved brand's name, palette, fonts, target locations or industry. Only
// the fields provided are changed; the logo is managed separately.
export async function updateBuilder(
  id: string,
  body: {
    name?: string;
    themeHeading?: string;
    themeSecondary?: string | null;
    themeAccent?: string | null;
    fonts?: string[];
    targetLocations?: string[];
    industry?: string | null;
  },
): Promise<void> {
  const res = await fetch(`/api/admin/builders/${id}`, {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Could not update brand (${res.status})`);
}

export async function deleteBuilder(id: string): Promise<void> {
  await fetch(`/api/admin/builders/${id}`, { method: "DELETE" });
}

export async function saveProfile(
  body: Partial<BuilderProfile> & { builderId: string; name: string },
): Promise<{ id: string }> {
  return jsonOrThrow(
    await fetch("/api/admin/builders/profiles", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    }),
    "Could not save profile",
  );
}

export async function deleteProfile(id: string): Promise<void> {
  await fetch(`/api/admin/builders/profiles/${id}`, { method: "DELETE" });
}

export async function setUserGroup(
  email: string,
  groupId: string | null,
): Promise<void> {
  await fetch(`/api/admin/users/${encodeURIComponent(email)}/group`, {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ groupId }),
  });
}

export interface AuditEntry {
  id: number;
  createdAt: string | null;
  actorEmail: string | null;
  action: string;
  targetType: string | null;
  targetId: string | null;
  detail: Record<string, unknown> | null;
  cost: number;
}

export async function getAudit(filters: {
  actor?: string;
  action?: string;
  minCost?: string;
  dateFrom?: string;
  dateTo?: string;
}): Promise<AuditEntry[]> {
  const qs = new URLSearchParams();
  if (filters.actor) qs.set("actor", filters.actor);
  if (filters.action) qs.set("action", filters.action);
  if (filters.minCost) qs.set("min_cost", filters.minCost);
  if (filters.dateFrom) qs.set("date_from", filters.dateFrom);
  if (filters.dateTo) qs.set("date_to", filters.dateTo);
  const res = await fetch(`/api/admin/audit?${qs.toString()}`);
  if (!res.ok) throw new Error(`Could not load audit log (${res.status})`);
  return res.json();
}

export interface ReferenceHealth {
  state: "green" | "amber" | "red";
  loaded: number;
  total: number;
  stale?: string[];
}

export async function getReferenceHealth(): Promise<ReferenceHealth> {
  const res = await fetch("/api/reference/health");
  if (!res.ok) return { state: "red", loaded: 0, total: 0 };
  return res.json();
}

// The interface brand for the signed-in user, drawn from their group's brand.
// The logo bytes are served separately at /api/builders/:builderId/logo.
export interface Brand {
  builderId: string | null;
  name: string | null;
  themeHeading?: string | null;
  themeSecondary?: string | null;
  themeAccent?: string | null;
  fonts?: string[];
  hasLogo?: boolean;
  /** The owning group (company) and the brand's sector, for theming and copy. */
  groupId?: string | null;
  companyName?: string | null;
  industry?: string | null;
}

export interface AppUser {
  email: string | null;
  name: string | null;
  role: string;
  builderGroupId?: string | null;
  /** Brands this user may switch between; the active one white-labels the app. */
  brands?: Brand[];
}

// The brand the user has selected as active, read from localStorage so it can be
// forwarded to the worker (which scopes profiles and the AI allowance to it).
const ACTIVE_BRAND_KEY = "landlynk.activeBrandId";

export function getActiveBrandId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(ACTIVE_BRAND_KEY);
}

export function setActiveBrandId(id: string | null): void {
  if (typeof window === "undefined") return;
  if (id) window.localStorage.setItem(ACTIVE_BRAND_KEY, id);
  else window.localStorage.removeItem(ACTIVE_BRAND_KEY);
}

function activeBrandHeaders(): Record<string, string> {
  const id = getActiveBrandId();
  return id ? { "x-active-brand": id } : {};
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

// Upload a reference file to the worker in chunks. Slicing the file into parts
// lets an admin upload a multi-GB archive (e.g. a 1.6GB data.police.uk crime
// zip) straight from the browser without hitting request size or timeout
// limits, and with no external storage. Chunks are sent strictly in order; the
// worker reassembles them on disk and loads the file once the last chunk lands.
// onProgress reports completion as a 0..1 fraction.
export async function uploadReference(
  dataset: string,
  file: File,
  params: Record<string, string>,
  onProgress?: (fraction: number) => void,
): Promise<void> {
  const CHUNK_SIZE = 8 * 1024 * 1024;
  const totalChunks = Math.max(1, Math.ceil(file.size / CHUNK_SIZE));
  const uploadId = crypto.randomUUID();
  const areaType = params.areaType ?? "MSOA";
  for (let i = 0; i < totalChunks; i++) {
    const blob = file.slice(i * CHUNK_SIZE, (i + 1) * CHUNK_SIZE);
    const res = await fetch(`/api/admin/reference/${dataset}/upload-chunk`, {
      method: "POST",
      headers: {
        "content-type": "application/octet-stream",
        "x-upload-id": uploadId,
        "x-chunk-index": String(i),
        "x-total-chunks": String(totalChunks),
        "x-filename": encodeURIComponent(file.name),
        "x-area-type": areaType,
      },
      body: blob,
    });
    if (!res.ok) {
      const detail = await res
        .json()
        .then((b) => b?.detail ?? b?.error)
        .catch(() => null);
      throw new Error(detail ?? `Upload failed (${res.status})`);
    }
    onProgress?.((i + 1) / totalChunks);
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
