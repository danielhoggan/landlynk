import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { getBattlecard } from "@/lib/workerClient";

// GET /api/catchments/:id/battlecards/:areaCode. Serve one area's stored
// Battlecard payload. Served from stored data, no recompute (SCOPING.md 5.2).
export async function GET(
  _request: Request,
  { params }: { params: { id: string; areaCode: string } },
) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const battlecard = await getBattlecard(
      params.id,
      params.areaCode,
      sessionUser(session),
    );
    return NextResponse.json(battlecard);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Not found";
    const status = message.includes("403") ? 403 : 404;
    return NextResponse.json({ error: message }, { status });
  }
}
