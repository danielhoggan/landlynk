import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { userHeaders } from "@/lib/workerClient";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

// GET /api/catchments/:id/competitors. Competitor developments (national
// planning applications) inside the catchment. The worker persists a snapshot
// per run; ?refresh=1 forces a live re-query.
export async function GET(
  request: Request,
  { params }: { params: { id: string } },
) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const refresh =
    new URL(request.url).searchParams.get("refresh") === "1" ? "?refresh=true" : "";
  const res = await fetch(
    `${WORKER_BASE_URL}/catchments/${params.id}/competitors${refresh}`,
    { headers: userHeaders(sessionUser(session)), cache: "no-store" },
  );
  if (!res.ok) return NextResponse.json({ sites: [] });
  return NextResponse.json(await res.json());
}
