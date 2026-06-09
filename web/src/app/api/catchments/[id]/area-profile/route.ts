import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { userHeaders } from "@/lib/workerClient";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

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
    headers: { "content-type": "application/json", ...userHeaders(sessionUser(session)) },
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
