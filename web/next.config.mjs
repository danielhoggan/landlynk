/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Standalone output for a small production container image (Railway deploy).
  output: "standalone",
  // The web app is a thin client. Heavy geospatial work runs in the Python
  // worker, never in a Next.js request cycle (CLAUDE.md, architecture rules).
};

export default nextConfig;
