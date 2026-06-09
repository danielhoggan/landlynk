import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { userHeaders } from "@/lib/workerClient";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

// PUT /api/models/default. Set the default AI model. Admin only.
export async function PUT(request: Request) {
  const session = await requireSession();
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const body = await request.json().catch(() => ({}));
  const res = await fetch(`${WORKER_BASE_URL}/admin/models/default`, {
    method: "PUT",
    headers: { "content-type": "application/json", ...userHeaders(sessionUser(session)) },
    body: JSON.stringify({ model: String(body?.model ?? "") }),
  });
  if (!res.ok) {
    return NextResponse.json({ error: "Could not set model" }, { status: res.status });
  }
  return new NextResponse(null, { status: 204 });
}
