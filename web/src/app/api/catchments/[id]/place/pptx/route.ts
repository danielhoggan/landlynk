import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { userHeaders } from "@/lib/workerClient";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

// GET /api/catchments/:id/place/pptx. The Place setting pack deck download.
export async function GET(
  _request: Request,
  { params }: { params: { id: string } },
) {
  const session = await requireSession();
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const res = await fetch(
    `${WORKER_BASE_URL}/catchments/${params.id}/place/pptx`,
    { headers: userHeaders(sessionUser(session)), cache: "no-store" },
  );
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(
      { error: data?.detail ?? "Could not build the pack" },
      { status: res.status },
    );
  }
  return new NextResponse(res.body, {
    headers: {
      "content-type":
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
      "content-disposition": 'attachment; filename="landlynk-place-pack.pptx"',
    },
  });
}
