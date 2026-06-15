import { adminProxy } from "@/lib/adminProxy";

export async function PUT(
  request: Request,
  { params }: { params: { id: string } },
) {
  return adminProxy("PUT", `/admin/builders/${params.id}`, await request.json());
}

export async function DELETE(
  _request: Request,
  { params }: { params: { id: string } },
) {
  return adminProxy("DELETE", `/admin/builders/${params.id}`);
}
