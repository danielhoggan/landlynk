import { adminProxy } from "@/lib/adminProxy";

export async function GET(request: Request) {
  const groupId = new URL(request.url).searchParams.get("groupId");
  const q = groupId ? `?group_id=${encodeURIComponent(groupId)}` : "";
  return adminProxy("GET", `/admin/builders${q}`);
}
export async function POST(request: Request) {
  return adminProxy("POST", "/admin/builders", await request.json());
}
