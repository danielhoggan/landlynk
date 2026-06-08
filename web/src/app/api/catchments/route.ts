import { NextResponse } from "next/server";
import { requireSession } from "@/lib/requireSession";
import { submitCatchmentJob } from "@/lib/workerClient";
import type { CatchmentInput } from "@/lib/types/catchment";

// POST /api/catchments. Submit a catchment job. Thin handler: auth, then hand
// off to the worker. No geospatial work here.
export async function POST(request: Request) {
  const session = await requireSession();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  let input: CatchmentInput;
  try {
    input = (await request.json()) as CatchmentInput;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  if (!input?.value || !input?.kind || !input?.developmentName) {
    return NextResponse.json(
      { error: "value, kind and developmentName are required" },
      { status: 400 },
    );
  }

  const job = await submitCatchmentJob(input);
  return NextResponse.json(job, { status: 202 });
}
