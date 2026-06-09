import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { setArchived } from "@/lib/workerClient";

// POST /api/catchments/:id/archive. Body { archived: boolean }. Owner or admin.
export async function POST(
  request: Request,
  { params }: { params: { id: string } },
) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const body = await request.json().catch(() => ({}));
  const archived = body?.archived !== false;
  try {
    await setArchived(params.id, archived, sessionUser(session));
  } catch (err) {
    const message = err instanceof Error ? err.message : "Archive failed";
    const status = message.includes("403") ? 403 : 502;
    return NextResponse.json({ error: message }, { status });
  }
  return new NextResponse(null, { status: 204 });
}
