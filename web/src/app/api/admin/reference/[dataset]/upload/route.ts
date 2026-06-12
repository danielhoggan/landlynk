import { NextResponse } from "next/server";
import { requireSession } from "@/lib/requireSession";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";
const ADMIN_TOKEN = process.env.WORKER_ADMIN_TOKEN ?? "";

// POST /api/admin/reference/:dataset/upload. Forward a multipart file upload to
// the worker, which parses and loads it into PostGIS. Used for sources with no
// stable URL to fetch (e.g. a data.police.uk crime archive the admin builds and
// downloads). The body is streamed through so large archives are not buffered.
export async function POST(
  request: Request,
  { params }: { params: { dataset: string } },
) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const res = await fetch(
    `${WORKER_BASE_URL}/admin/reference/${params.dataset}/upload`,
    {
      method: "POST",
      headers: {
        "content-type": request.headers.get("content-type") ?? "",
        ...(ADMIN_TOKEN ? { "x-admin-token": ADMIN_TOKEN } : {}),
      },
      body: request.body,
      // Required by Node's fetch when streaming a request body.
      duplex: "half",
      cache: "no-store",
    } as RequestInit & { duplex: "half" },
  );
  return NextResponse.json(await res.json().catch(() => ({})), {
    status: res.status,
  });
}
