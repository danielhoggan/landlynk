import { NextResponse } from "next/server";
import { requireSession } from "@/lib/requireSession";
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

  const battlecard = await getBattlecard(params.id, params.areaCode);
  return NextResponse.json(battlecard);
}
