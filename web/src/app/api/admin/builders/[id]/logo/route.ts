import { adminProxy } from "@/lib/adminProxy";

// POST /api/admin/builders/:id/logo — base64 logo upload, forwarded to the
// worker which commits it to GitHub. Admin only.
export async function POST(
  request: Request,
  { params }: { params: { id: string } },
) {
  return adminProxy(
    "POST",
    `/admin/builders/${params.id}/logo`,
    await request.json(),
  );
}
