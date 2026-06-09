import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { addShares, listShares } from "@/lib/workerClient";

// GET /api/catchments/:id/shares. List the emails a catchment is shared with.
export async function GET(
  _request: Request,
  { params }: { params: { id: string } },
) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  try {
    return NextResponse.json(await listShares(params.id, sessionUser(session)));
  } catch (err) {
    const message = err instanceof Error ? err.message : "Could not load shares";
    const status = message.includes("403") ? 403 : 502;
    return NextResponse.json({ error: message }, { status });
  }
}

// POST /api/catchments/:id/shares. Body { emails: string[] }. Owner or admin.
export async function POST(
  request: Request,
  { params }: { params: { id: string } },
) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const body = await request.json().catch(() => ({}));
  const emails: string[] = Array.isArray(body?.emails) ? body.emails : [];
  try {
    await addShares(params.id, emails, sessionUser(session));
  } catch (err) {
    const message = err instanceof Error ? err.message : "Share failed";
    const status = message.includes("403") ? 403 : 502;
    return NextResponse.json({ error: message }, { status });
  }
  return new NextResponse(null, { status: 204 });
}
