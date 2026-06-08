// Enforce the Azure AD SSO gate on every page and data route. The gate stays
// intact on every route that touches data or generates output
// (house-standards.md, security and access). Unauthenticated requests are
// redirected to the sign-in page.
export { default } from "next-auth/middleware";

export const config = {
  // Protect everything except the auth handler, the sign-in page and static
  // assets. The next-auth handler must stay public so sign-in can complete.
  matcher: ["/((?!api/auth|signin|_next/static|_next/image|favicon.ico).*)"],
};
