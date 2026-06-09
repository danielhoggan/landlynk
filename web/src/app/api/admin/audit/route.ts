import { adminProxy } from "@/lib/adminProxy";

// GET /api/admin/audit — forwards filters (actor, action, minCost, dateFrom,
// dateTo) to the worker. Admin only (enforced by the worker).
export async function GET(request: Request) {
  const qs = new URL(request.url).searchParams.toString();
  return adminProxy("GET", `/admin/audit${qs ? `?${qs}` : ""}`);
}
