import { NextResponse } from "next/server";
import { requireSession, sessionUser } from "@/lib/requireSession";
import { userHeaders } from "@/lib/workerClient";

const WORKER_BASE_URL = process.env.WORKER_BASE_URL ?? "http://localhost:8000";

// POST /api/catchments/:id/verdict. A compact whole-catchment appraisal verdict
// (price fit and addressable demand) for the housebuilder intents.
export async function POST(
  request: Request,
  { params }: { params: { id: string } },
) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const res = await fetch(`${WORKER_BASE_URL}/catchments/${params.id}/verdict`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...userHeaders(sessionUser(session)),
    },
    body: JSON.stringify({ scope: "whole" }),
    cache: "no-store",
  });
  if (!res.ok) {
    return NextResponse.json({ error: "No verdict" }, { status: res.status });
  }
  return NextResponse.json(await res.json());
}
