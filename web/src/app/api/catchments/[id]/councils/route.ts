import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { userHeaders } from "@/lib/workerClient";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

// GET /api/catchments/:id/councils. Local authority boundaries intersecting the
// catchment, for the map's council overlay. Empty when LA boundaries are not
// loaded, so the toggle degrades gracefully.
export async function GET(
  _request: Request,
  { params }: { params: { id: string } },
) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const res = await fetch(
    `${WORKER_BASE_URL}/catchments/${params.id}/councils`,
    { headers: userHeaders(sessionUser(session)), cache: "no-store" },
  );
  if (!res.ok) {
    return NextResponse.json({ councils: [] });
  }
  return NextResponse.json(await res.json());
}
