import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { setUserRole } from "@/lib/workerClient";

// PUT /api/users/:email/role. Body { role }. Admin only.
export async function PUT(
  request: Request,
  { params }: { params: { email: string } },
) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const body = await request.json().catch(() => ({}));
  const role = String(body?.role ?? "");
  try {
    await setUserRole(
      decodeURIComponent(params.email),
      role,
      sessionUser(session),
    );
  } catch (err) {
    const message = err instanceof Error ? err.message : "Update failed";
    const status = message.includes("403") ? 403 : 502;
    return NextResponse.json({ error: message }, { status });
  }
  return new NextResponse(null, { status: 204 });
}
