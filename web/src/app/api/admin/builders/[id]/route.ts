import { adminProxy } from "@/lib/adminProxy";

export async function DELETE(
  _request: Request,
  { params }: { params: { id: string } },
) {
  return adminProxy("DELETE", `/admin/builders/${params.id}`);
}
