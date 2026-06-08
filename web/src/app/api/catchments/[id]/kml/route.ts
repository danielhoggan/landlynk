import { NextResponse } from "next/server";
import { requireSession } from "@/lib/requireSession";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

// GET /api/catchments/:id/kml. Stream the worker-rendered KML through the
// SSO-gated API layer for Google Earth.
export async function GET(
  _request: Request,
  { params }: { params: { id: string } },
) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const res = await fetch(`${WORKER_BASE_URL}/catchments/${params.id}/kml`, {
    cache: "no-store",
  });
  if (!res.ok) {
    return NextResponse.json(
      { error: "Catchment not found" },
      { status: res.status },
    );
  }

  const body = await res.text();
  return new NextResponse(body, {
    status: 200,
    headers: {
      "content-type": "application/vnd.google-earth.kml+xml",
      "content-disposition": `attachment; filename="catchment-${params.id}.kml"`,
    },
  });
}
