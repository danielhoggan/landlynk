import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { removeShare } from "@/lib/workerClient";

// DELETE /api/catchments/:id/shares/:email. Revoke a share. Owner or admin.
export async function DELETE(
  _request: Request,
  { params }: { params: { id: string; email: string } },
) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  try {
    await removeShare(
      params.id,
      decodeURIComponent(params.email),
      sessionUser(session),
    );
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unshare failed";
    const status = message.includes("403") ? 403 : 502;
    return NextResponse.json({ error: message }, { status });
  }
  return new NextResponse(null, { status: 204 });
}
