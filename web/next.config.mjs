// Security response headers. Conservative on purpose: no strict CSP yet, so the
// MapLibre map (open tiles, blob workers) and the Azure AD redirect keep working.
// These harden the app and signal legitimacy; the Safe Browsing flag itself is
// cleared via a Google Search Console review, not headers.
const securityHeaders = [
  {
    key: "Strict-Transport-Security",
    value: "max-age=63072000; includeSubDomains; preload",
  },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=()",
  },
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Standalone output for a small production container image (Railway deploy).
  output: "standalone",
  // The web app is a thin client. Heavy geospatial work runs in the Python
  // worker, never in a Next.js request cycle (CLAUDE.md, architecture rules).
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
