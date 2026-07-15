import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { userHeaders } from "@/lib/workerClient";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

// GET /api/catchments/:id/place. The factual place profile (transit, dining,
// cycling) from OpenStreetMap, persisted per run. ?refresh=1 re-fetches.
export async function GET(
  request: Request,
  { params }: { params: { id: string } },
) {
  const session = await requireSession();
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const refresh =
    new URL(request.url).searchParams.get("refresh") === "1" ? "?refresh=true" : "";
  const res = await fetch(
    `${WORKER_BASE_URL}/catchments/${params.id}/place${refresh}`,
    { headers: userHeaders(sessionUser(session)), cache: "no-store" },
  );
  const data = await res.json().catch(() => ({ place: null }));
  return NextResponse.json(data, { status: res.ok ? 200 : res.status });
}
