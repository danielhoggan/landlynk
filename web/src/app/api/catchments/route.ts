import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { listCatchments, submitCatchmentJob } from "@/lib/workerClient";

// GET /api/catchments. List the caller's catchments (own plus shared) for the
// history view. Pass ?archived=true for the archived area.
export async function GET(request: Request) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const archived =
    new URL(request.url).searchParams.get("archived") === "true";
  return NextResponse.json(
    await listCatchments(sessionUser(session), archived),
  );
}

// POST /api/catchments. Submit a catchment job. Thin handler: auth, then hand
// off to the worker. No geospatial work here.
export async function POST(request: Request) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  let input: Record<string, unknown>;
  try {
    input = (await request.json()) as Record<string, unknown>;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  if (!input?.value || !input?.kind || !input?.developmentName) {
    return NextResponse.json(
      { error: "value, kind and developmentName are required" },
      { status: 400 },
    );
  }

  try {
    const job = await submitCatchmentJob(input, sessionUser(session));
    return NextResponse.json(job, { status: 202 });
  } catch (err) {
    // The worker (or the call to it) failed. Pass the detail through so the UI
    // shows the real cause instead of a generic 500.
    const message = err instanceof Error ? err.message : "Worker unavailable";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
