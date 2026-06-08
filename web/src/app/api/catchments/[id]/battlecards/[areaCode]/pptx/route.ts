import { NextResponse } from "next/server";
import { requireSession } from "@/lib/requireSession";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";
const PPTX_MIME =
  "application/vnd.openxmlformats-officedocument.presentationml.presentation";

// GET /api/catchments/:id/battlecards/:areaCode/pptx. Stream the worker-rendered
// PPTX deck through the SSO-gated API layer.
export async function GET(
  _request: Request,
  { params }: { params: { id: string; areaCode: string } },
) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const res = await fetch(
    `${WORKER_BASE_URL}/catchments/${params.id}/battlecards/${params.areaCode}/pptx`,
    { cache: "no-store" },
  );
  if (!res.ok) {
    return NextResponse.json(
      { error: "Battlecard not found" },
      { status: res.status },
    );
  }

  const body = await res.arrayBuffer();
  return new NextResponse(body, {
    status: 200,
    headers: {
      "content-type": PPTX_MIME,
      "content-disposition": `attachment; filename="battlecard-${params.areaCode}.pptx"`,
    },
  });
}
