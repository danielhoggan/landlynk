import { adminProxy } from "@/lib/adminProxy";

export async function GET() {
  return adminProxy("GET", "/admin/builders/groups");
}
export async function POST(request: Request) {
  return adminProxy("POST", "/admin/builders/groups", await request.json());
}
