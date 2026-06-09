import { adminProxy } from "@/lib/adminProxy";

export async function PUT(
  request: Request,
  { params }: { params: { email: string } },
) {
  return adminProxy(
    "PUT",
    `/admin/users/${encodeURIComponent(params.email)}/group`,
    await request.json(),
  );
}
