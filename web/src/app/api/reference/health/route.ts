import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { userHeaders } from "@/lib/workerClient";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

// GET /api/reference/health. RAG summary for the status dot (no source detail),
// available to any signed-in user.
export async function GET() {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const res = await fetch(`${WORKER_BASE_URL}/reference/health`, {
    headers: userHeaders(sessionUser(session)),
    cache: "no-store",
  });
  if (!res.ok) {
    return NextResponse.json({ state: "red", loaded: 0, total: 0 });
  }
  return NextResponse.json(await res.json());
}
