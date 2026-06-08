import { NextResponse } from "next/server";
import { requireSession } from "@/lib/requireSession";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

// POST /api/catchments/:id/shortlist/pdf. Combine the selected areas' Battlecards
// into one PDF, streamed through the SSO-gated API layer.
export async function POST(
  request: Request,
  { params }: { params: { id: string } },
) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const payload = await request.json().catch(() => null);
  const areaCodes: unknown = payload?.areaCodes;
  if (!Array.isArray(areaCodes) || areaCodes.length === 0) {
    return NextResponse.json(
      { error: "Select at least one area" },
      { status: 400 },
    );
  }

  const res = await fetch(`${WORKER_BASE_URL}/catchments/${params.id}/shortlist/pdf`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ area_codes: areaCodes }),
    cache: "no-store",
  });
  if (!res.ok) {
    return NextResponse.json(
      { error: "Could not build shortlist" },
      { status: res.status },
    );
  }

  const body = await res.arrayBuffer();
  return new NextResponse(body, {
    status: 200,
    headers: {
      "content-type": "application/pdf",
      "content-disposition": 'attachment; filename="landlynk-shortlist.pdf"',
    },
  });
}
