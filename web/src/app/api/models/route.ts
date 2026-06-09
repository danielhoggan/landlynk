import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { userHeaders } from "@/lib/workerClient";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

// GET /api/models. Available AI models and the admin-chosen default. Admin only.
export async function GET() {
  const session = await requireSession();
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const res = await fetch(`${WORKER_BASE_URL}/admin/models`, {
    headers: userHeaders(sessionUser(session)),
    cache: "no-store",
  });
  if (!res.ok) {
    return NextResponse.json({ error: "Forbidden" }, { status: res.status });
  }
  return NextResponse.json(await res.json());
}
