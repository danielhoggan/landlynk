// Browser-side client for the Next API routes. The routes proxy to the worker
// behind the Azure AD SSO gate.

import type { Battlecard } from "./types/battlecard";
import type { Catchment } from "./types/catchment";

export interface SubmitPayload {
  kind: "postcode" | "gridref";
  value: string;
  developmentName: string;
  town?: string;
  strapline?: string;
  lifestylePillars?: string[];
  developmentFeatures?: string[];
  config?: {
    priceBand?: { from: number; to: number };
    bedRange?: string;
    driveTimeMinutes?: number;
    overlapThreshold?: number;
  };
}

export async function submitCatchment(payload: SubmitPayload): Promise<{ id: string }> {
  const res = await fetch("/api/catchments", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`Submission failed (${res.status})`);
  return res.json();
}

export async function getCatchment(id: string): Promise<Catchment> {
  const res = await fetch(`/api/catchments/${id}`);
  if (!res.ok) throw new Error(`Could not load catchment (${res.status})`);
  return res.json();
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
  { intervalMs = 1500, timeoutMs = 120_000 }: { intervalMs?: number; timeoutMs?: number } = {},
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
