import { adminProxy } from "@/lib/adminProxy";

// GET /api/admin/costs — AI cost report (date filters), forwarded to the worker.
export async function GET(request: Request) {
  const qs = new URL(request.url).searchParams.toString();
  return adminProxy("GET", `/admin/costs${qs ? `?${qs}` : ""}`);
}
