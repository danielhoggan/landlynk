import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { userHeaders } from "@/lib/workerClient";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

const PPTX_MEDIA_TYPE =
  "application/vnd.openxmlformats-officedocument.presentationml.presentation";

// POST /api/catchments/:id/shortlist/pptx. Combine the selected areas' Battlecards
// into one deck, streamed through the SSO-gated API layer.
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

  const res = await fetch(`${WORKER_BASE_URL}/catchments/${params.id}/shortlist/pptx`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...userHeaders(sessionUser(session)),
    },
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
      "content-type": PPTX_MEDIA_TYPE,
      "content-disposition": 'attachment; filename="landlynk-shortlist.pptx"',
    },
  });
}
