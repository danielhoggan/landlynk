import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { deleteCatchmentJob, getCatchment } from "@/lib/workerClient";

// GET /api/catchments/:id. Read a catchment with its scored, ranked areas.
export async function GET(
  _request: Request,
  { params }: { params: { id: string } },
) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const catchment = await getCatchment(params.id, sessionUser(session));
  return NextResponse.json(catchment);
}

// DELETE /api/catchments/:id. Remove a saved catchment. Admin only; the worker
// returns 403 for non-admins.
export async function DELETE(
  _request: Request,
  { params }: { params: { id: string } },
) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    await deleteCatchmentJob(params.id, sessionUser(session));
  } catch (err) {
    const message = err instanceof Error ? err.message : "Delete failed";
    const status = message.includes("403") ? 403 : 502;
    return NextResponse.json({ error: message }, { status });
  }
  return new NextResponse(null, { status: 204 });
}
