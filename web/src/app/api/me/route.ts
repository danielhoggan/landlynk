import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { getMe } from "@/lib/workerClient";

// GET /api/me. The caller's account record (email, name, role).
export async function GET() {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  try {
    return NextResponse.json(await getMe(sessionUser(session)));
  } catch {
    // Fall back to the session identity if the worker directory is unavailable.
    const u = sessionUser(session);
    return NextResponse.json({
      email: u.email ?? null,
      name: u.name ?? null,
      role: "internal-user",
    });
  }
}
