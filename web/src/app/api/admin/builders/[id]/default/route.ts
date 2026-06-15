import { adminProxy } from "@/lib/adminProxy";

// POST /api/admin/builders/:id/default — make this brand the one that
// white-labels the app interface for its group. Admin only.
export async function POST(
  _request: Request,
  { params }: { params: { id: string } },
) {
  return adminProxy("POST", `/admin/builders/${params.id}/default`);
}
