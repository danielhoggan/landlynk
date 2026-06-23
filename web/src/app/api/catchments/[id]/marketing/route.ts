import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { userHeaders, activeBrandHeader } from "@/lib/workerClient";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

// GET /api/catchments/:id/marketing. Return an already-generated Marketing
// Activation playbook (or { playbook: null }). Internal staff only; read-only,
// so it never spends an LLM call.
export async function GET(
  request: Request,
  { params }: { params: { id: string } },
) {
  const session = await requireSession();
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const res = await fetch(`${WORKER_BASE_URL}/catchments/${params.id}/marketing`, {
    headers: {
      ...userHeaders(sessionUser(session)),
      ...activeBrandHeader(request),
    },
    cache: "no-store",
  });
  const data = await res.json().catch(() => ({ playbook: null }));
  return NextResponse.json(data, { status: res.ok ? 200 : res.status });
}

// POST /api/catchments/:id/marketing. Generate (or refresh) the Marketing
// Activation playbook for the whole catchment. Internal staff only; this spends
// an LLM call, so the client confirms the cost before posting.
export async function POST(
  request: Request,
  { params }: { params: { id: string } },
) {
  const session = await requireSession();
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const body = await request.json().catch(() => ({}));
  const res = await fetch(`${WORKER_BASE_URL}/catchments/${params.id}/marketing`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...userHeaders(sessionUser(session)),
      ...activeBrandHeader(request),
    },
    body: JSON.stringify({
      intent: body?.intent ?? null,
      model: body?.model ?? null,
      refresh: body?.refresh === true,
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    return NextResponse.json(
      { error: data?.detail ?? "Could not generate playbook" },
      { status: res.status },
    );
  }
  return NextResponse.json(data);
}
