import { NextResponse } from "next/server";
import { requireSession } from "@/lib/requireSession";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";
const ADMIN_TOKEN = process.env.WORKER_ADMIN_TOKEN ?? "";

// POST /api/admin/reference/:dataset. Trigger a server-side reference data load
// in the worker (it downloads the open data and loads PostGIS). No local steps.
export async function POST(
  request: Request,
  { params }: { params: { dataset: string } },
) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const body = await request.json().catch(() => ({}));
  const res = await fetch(
    `${WORKER_BASE_URL}/admin/reference/${params.dataset}`,
    {
      method: "POST",
      headers: {
        "content-type": "application/json",
        ...(ADMIN_TOKEN ? { "x-admin-token": ADMIN_TOKEN } : {}),
      },
      body: JSON.stringify(body),
      cache: "no-store",
    },
  );
  return NextResponse.json(await res.json().catch(() => ({})), {
    status: res.status,
  });
}
