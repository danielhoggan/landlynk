import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { userHeaders } from "@/lib/workerClient";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

// POST /api/catchments/:id/combined/pdf. Merge selected areas (or the whole
// catchment) into one aggregate Battlecard, streamed through the SSO gate.
export async function POST(
  request: Request,
  { params }: { params: { id: string } },
) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const payload = await request.json().catch(() => ({}));
  const body = {
    area_codes: Array.isArray(payload?.areaCodes) ? payload.areaCodes : [],
    scope: payload?.scope === "whole" ? "whole" : "selection",
  };
  const res = await fetch(`${WORKER_BASE_URL}/catchments/${params.id}/combined/pdf`, {
    method: "POST",
    headers: { "content-type": "application/json", ...userHeaders(sessionUser(session)) },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) {
    return NextResponse.json(
      { error: "Could not build combined Battlecard" },
      { status: res.status },
    );
  }
  return new NextResponse(await res.arrayBuffer(), {
    status: 200,
    headers: {
      "content-type": "application/pdf",
      "content-disposition": 'attachment; filename="landlynk-combined.pdf"',
    },
  });
}
