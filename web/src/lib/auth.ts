import type { NextAuthOptions } from "next-auth";
import AzureADProvider from "next-auth/providers/azure-ad";

// next-auth v4 with Azure AD SSO. SSO is the only auth path. Do not add a local
// password flow (house-standards.md, security and access). The Azure AD SSO
// gate stays intact on every route that touches data or generates output.
export const authOptions: NextAuthOptions = {
  providers: [
    AzureADProvider({
      clientId: process.env.AZURE_AD_CLIENT_ID ?? "",
      clientSecret: process.env.AZURE_AD_CLIENT_SECRET ?? "",
      tenantId: process.env.AZURE_AD_TENANT_ID ?? "",
    }),
  ],
  session: {
    strategy: "jwt",
  },
  callbacks: {
    async session({ session, token }) {
      if (session.user && token.sub) {
        // Surface the subject id for audit (created_by on catchments).
        (session.user as { id?: string }).id = token.sub;
      }
      return session;
    },
  },
};
