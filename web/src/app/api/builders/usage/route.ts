import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { userHeaders, activeBrandHeader } from "@/lib/workerClient";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

// GET /api/builders/usage. The caller's AI generation allowance this month,
// scoped to their active brand's group.
export async function GET(request: Request) {
  const session = await requireSession();
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  const res = await fetch(`${WORKER_BASE_URL}/builders/usage`, {
    headers: {
      ...userHeaders(sessionUser(session)),
      ...activeBrandHeader(request),
    },
    cache: "no-store",
  });
  if (!res.ok) return NextResponse.json({ metered: false }, { status: 200 });
  return NextResponse.json(await res.json());
}
