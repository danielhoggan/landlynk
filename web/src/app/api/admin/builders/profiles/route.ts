import { adminProxy } from "@/lib/adminProxy";

export async function POST(request: Request) {
  return adminProxy("POST", "/admin/builders/profiles", await request.json());
}
