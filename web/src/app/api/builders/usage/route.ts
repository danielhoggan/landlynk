import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { userHeaders } from "@/lib/workerClient";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

// GET /api/builders/usage. The caller's AI generation allowance this month.
export async function GET() {
  const session = await requireSession();
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const res = await fetch(`${WORKER_BASE_URL}/builders/usage`, {
    headers: userHeaders(sessionUser(session)),
    cache: "no-store",
  });
  if (!res.ok) return NextResponse.json({ metered: false }, { status: 200 });
  return NextResponse.json(await res.json());
}
