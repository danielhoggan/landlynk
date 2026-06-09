import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { getMySettings, putMySettings } from "@/lib/workerClient";

// GET /api/me/settings. The caller's stored account settings (or null).
export async function GET() {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  try {
    return NextResponse.json(await getMySettings(sessionUser(session)));
  } catch {
    return NextResponse.json({ settings: null });
  }
}

// PUT /api/me/settings. Body { settings: {...} }. Persisted to the account.
export async function PUT(request: Request) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const body = await request.json().catch(() => ({}));
  const settings = (body?.settings ?? {}) as Record<string, unknown>;
  try {
    await putMySettings(settings, sessionUser(session));
  } catch (err) {
    const message = err instanceof Error ? err.message : "Save failed";
    return NextResponse.json({ error: message }, { status: 502 });
  }
  return new NextResponse(null, { status: 204 });
}
