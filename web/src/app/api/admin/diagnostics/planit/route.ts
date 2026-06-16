import { adminProxy } from "@/lib/adminProxy";

// GET /api/admin/diagnostics/planit — probe the live competitor (PlanIt) feed.
export async function GET() {
  return adminProxy("GET", "/admin/diagnostics/planit");
}
