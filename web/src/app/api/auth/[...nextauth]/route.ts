import NextAuth from "next-auth";
import { authOptions } from "@/lib/auth";

// next-auth v4 App Router handler. Azure AD SSO only.
const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
