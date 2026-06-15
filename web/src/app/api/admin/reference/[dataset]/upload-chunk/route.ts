import { NextResponse } from "next/server";
import { requireSession } from "@/lib/requireSession";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";
const ADMIN_TOKEN = process.env.WORKER_ADMIN_TOKEN ?? "";

// POST /api/admin/reference/:dataset/upload-chunk. Forward one chunk of a file
// upload to the worker, which appends it to a temp file and, on the last chunk,
// loads it into PostGIS. Chunking lets an admin upload a multi-GB archive (e.g.
// a data.police.uk crime zip) straight from the browser without hitting request
// size or timeout limits, and with no external storage. The chunk body is
// streamed through, so nothing is buffered here.
export async function POST(
  request: Request,
  { params }: { params: { dataset: string } },
) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const h = request.headers;
  const res = await fetch(
    `${WORKER_BASE_URL}/admin/reference/${params.dataset}/upload-chunk`,
    {
      method: "POST",
      headers: {
        "content-type": h.get("content-type") ?? "application/octet-stream",
        "x-upload-id": h.get("x-upload-id") ?? "",
        "x-chunk-index": h.get("x-chunk-index") ?? "",
        "x-total-chunks": h.get("x-total-chunks") ?? "",
        "x-filename": h.get("x-filename") ?? "",
        "x-area-type": h.get("x-area-type") ?? "MSOA",
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
