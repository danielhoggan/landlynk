import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { userHeaders } from "@/lib/workerClient";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

// Forward an admin call to the worker through the SSO gate, attaching the signed
// in identity. The worker enforces the admin role; this just relays.
export async function adminProxy(
  method: string,
  path: string,
  body?: unknown,
): Promise<NextResponse> {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const res = await fetch(`${WORKER_BASE_URL}${path}`, {
    method,
    headers: {
      "content-type": "application/json",
      ...userHeaders(sessionUser(session)),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (res.status === 204) return new NextResponse(null, { status: 204 });
  const data = await res.json().catch(() => ({}));
  return NextResponse.json(data, { status: res.status });
}
