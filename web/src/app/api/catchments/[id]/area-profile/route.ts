import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { userHeaders, activeBrandHeader } from "@/lib/workerClient";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

// GET /api/catchments/:id/area-profile. Return an already-cached whole-catchment
// profile (or { profile: null }). Read-only: never generates, never meters.
export async function GET(
  request: Request,
  { params }: { params: { id: string } },
) {
  const session = await requireSession();
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const res = await fetch(`${WORKER_BASE_URL}/catchments/${params.id}/area-profile`, {
    headers: {
      ...userHeaders(sessionUser(session)),
      ...activeBrandHeader(request),
    },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({ profile: null }));
  return NextResponse.json(data, { status: res.ok ? 200 : res.status });
}

// POST /api/catchments/:id/area-profile. Generate (or fetch cached) an AI Local
// Area Profile for the whole catchment or a selection.
export async function POST(
  request: Request,
  { params }: { params: { id: string } },
) {
  const session = await requireSession();
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const body = await request.json().catch(() => ({}));
  const res = await fetch(`${WORKER_BASE_URL}/catchments/${params.id}/area-profile`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...userHeaders(sessionUser(session)),
      ...activeBrandHeader(request),
    },
    body: JSON.stringify({
      scope: body?.scope === "selection" ? "selection" : "whole",
      area_codes: Array.isArray(body?.areaCodes) ? body.areaCodes : [],
      model: body?.model ?? null,
      refresh: body?.refresh === true,
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    return NextResponse.json(
      { error: data?.detail ?? "Could not generate profile" },
      { status: res.status },
    );
  }
  return NextResponse.json(data);
}
