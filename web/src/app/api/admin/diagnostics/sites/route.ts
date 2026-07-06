import { adminProxy } from "@/lib/adminProxy";

// GET /api/admin/diagnostics/sites — what the development-site table holds per
// source type, with coordinate sanity, for debugging the land layers.
export async function GET() {
  return adminProxy("GET", "/admin/diagnostics/sites");
}
