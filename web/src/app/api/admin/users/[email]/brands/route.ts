import { adminProxy } from "@/lib/adminProxy";

// GET/PUT /api/admin/users/:email/brands — the user's specific brand grants
// (independent of a whole-group grant). Admin only.
export async function GET(
  _request: Request,
  { params }: { params: { email: string } },
) {
  return adminProxy(
    "GET",
    `/admin/users/${encodeURIComponent(params.email)}/brands`,
  );
}

export async function PUT(
  request: Request,
  { params }: { params: { email: string } },
) {
  return adminProxy(
    "PUT",
    `/admin/users/${encodeURIComponent(params.email)}/brands`,
    await request.json(),
  );
}
