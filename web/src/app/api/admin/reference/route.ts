import { NextResponse } from "next/server";
import { requireSession } from "@/lib/requireSession";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";
const ADMIN_TOKEN = process.env.WORKER_ADMIN_TOKEN ?? "";

// GET /api/admin/reference. Reference data load status, from the worker.
export async function GET() {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const res = await fetch(`${WORKER_BASE_URL}/admin/reference/status`, {
    headers: ADMIN_TOKEN ? { "x-admin-token": ADMIN_TOKEN } : {},
    cache: "no-store",
  });
  return NextResponse.json(await res.json(), { status: res.status });
}
