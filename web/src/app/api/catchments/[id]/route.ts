import { NextResponse } from "next/server";
import { requireSession } from "@/lib/requireSession";
import { getCatchment } from "@/lib/workerClient";

// GET /api/catchments/:id. Read a catchment with its scored, ranked areas.
export async function GET(
  _request: Request,
  { params }: { params: { id: string } },
) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const catchment = await getCatchment(params.id);
  return NextResponse.json(catchment);
}
