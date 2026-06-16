import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { userHeaders } from "@/lib/workerClient";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

// GET /api/catchments/:id/competitors. Live competitor developments (national
// planning applications) inside the catchment, for the Find a site overlay.
export async function GET(
  _request: Request,
  { params }: { params: { id: string } },
) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const res = await fetch(
    `${WORKER_BASE_URL}/catchments/${params.id}/competitors`,
    { headers: userHeaders(sessionUser(session)), cache: "no-store" },
  );
  if (!res.ok) return NextResponse.json({ sites: [] });
  return NextResponse.json(await res.json());
}
