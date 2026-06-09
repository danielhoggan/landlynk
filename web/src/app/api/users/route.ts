import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { listUsers } from "@/lib/workerClient";

// GET /api/users. The user directory. Admin only; the worker returns 403 otherwise.
export async function GET() {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  try {
    return NextResponse.json(await listUsers(sessionUser(session)));
  } catch (err) {
    const message = err instanceof Error ? err.message : "Could not load users";
    const status = message.includes("403") ? 403 : 502;
    return NextResponse.json({ error: message }, { status });
  }
}
