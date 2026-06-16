import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { userHeaders } from "@/lib/workerClient";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

// GET /api/builders/:id/logo — stream a brand logo from the worker (which reads
// it from GitHub). Any signed-in user, so logos render in the UI.
export async function GET(
  _request: Request,
  { params }: { params: { id: string } },
) {
  const session = await requireSession();
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const res = await fetch(`${WORKER_BASE_URL}/builders/${params.id}/logo`, {
    headers: userHeaders(sessionUser(session)),
    cache: "no-store",
  });
  if (!res.ok) return new NextResponse(null, { status: 404 });
  return new NextResponse(await res.arrayBuffer(), {
    status: 200,
    headers: {
      "content-type": res.headers.get("content-type") ?? "image/png",
      // Revalidate so a replaced logo (served at the same URL) shows immediately
      // rather than a stale cached copy.
      "cache-control": "private, no-cache",
    },
  });
}
