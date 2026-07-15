import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { userHeaders, activeBrandHeader } from "@/lib/workerClient";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

// POST /api/catchments/:id/place/story. Generate (or fetch cached) the AI half
// of the Place setting pack: annual events and local history. Metered like the
// Local Area Profile.
export async function POST(
  request: Request,
  { params }: { params: { id: string } },
) {
  const session = await requireSession();
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const body = await request.json().catch(() => ({}));
  const res = await fetch(
    `${WORKER_BASE_URL}/catchments/${params.id}/place/story`,
    {
      method: "POST",
      headers: {
        "content-type": "application/json",
        ...userHeaders(sessionUser(session)),
        ...activeBrandHeader(request),
      },
      body: JSON.stringify({
        model: body?.model ?? null,
        refresh: body?.refresh === true,
      }),
    },
  );
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    return NextResponse.json(
      { error: data?.detail ?? "Could not generate the place story" },
      { status: res.status },
    );
  }
  return NextResponse.json(data);
}
