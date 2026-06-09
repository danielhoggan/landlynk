import { getServerSession } from "next-auth";
import { authOptions } from "./auth";
import type { UserCtx } from "./workerClient";

/**
 * Guard for API route handlers. Returns the session or null. Every route that
 * touches data or generates output must call this so the Azure AD SSO gate
 * stays intact (house-standards.md, security and access).
 */
export async function requireSession() {
  const session = await getServerSession(authOptions);
  return session ?? null;
}

/** The signed-in identity, forwarded to the private worker for scoping. */
export function sessionUser(session: {
  user?: { email?: string | null; name?: string | null } | null;
} | null): UserCtx {
  return { email: session?.user?.email, name: session?.user?.name };
}
